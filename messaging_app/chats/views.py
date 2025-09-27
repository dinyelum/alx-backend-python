# chats/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Conversation, Message, User
from .serializers import (
    ConversationSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer
)
from .permissions import IsParticipantOfConversation, IsMessageOwner


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating conversations.
    Users can only see conversations they are participants in.
    """
    permission_classes = [permissions.IsAuthenticated,
                          IsParticipantOfConversation]
    filter_backends = [filters.SearchFilter,
                       filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['participants__first_name',
                     'participants__last_name', 'participants__email']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    filterset_fields = ['participants__user_id']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    def get_queryset(self):
        """
        Return only conversations where the current user is a participant
        """
        messages_prefetch = Prefetch(
            'messages',
            queryset=Message.objects.select_related(
                'sender').order_by('sent_at')
        )

        queryset = Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related(
            'participants',
            messages_prefetch
        ).distinct()

        # Additional filtering
        participant_filter = self.request.query_params.get('participant')
        if participant_filter:
            queryset = queryset.filter(
                participants__user_id=participant_filter)

        return queryset

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        conversation = serializer.save()
        # Automatically add the current user as a participant
        conversation.participants.add(self.request.user)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating messages.
    Users can only see messages from conversations they are participants in.
    """
    permission_classes = [permissions.IsAuthenticated,
                          IsParticipantOfConversation, IsMessageOwner]
    filter_backends = [filters.SearchFilter,
                       filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['message_body', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['sent_at']
    ordering = ['-sent_at']
    filterset_fields = ['conversation__conversation_id', 'sender__user_id']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        """
        Return only messages from conversations where the current user is a participant
        """
        queryset = Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related('sender', 'conversation')

        # Additional filtering
        conversation_id = self.request.query_params.get('conversation')
        if conversation_id:
            queryset = queryset.filter(
                conversation__conversation_id=conversation_id)

        sender_id = self.request.query_params.get('sender')
        if sender_id:
            queryset = queryset.filter(sender__user_id=sender_id)

        search_term = self.request.query_params.get('search')
        if search_term:
            queryset = queryset.filter(
                Q(message_body__icontains=search_term) |
                Q(sender__first_name__icontains=search_term) |
                Q(sender__last_name__icontains=search_term)
            )

        return queryset.order_by('-sent_at')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """Automatically set the current user as the sender"""
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'], url_path='conversation/(?P<conversation_id>[^/.]+)')
    def conversation_messages(self, request, conversation_id=None):
        """
        Custom action to get all messages for a specific conversation
        """
        try:
            # Verify user has access to this conversation using our custom permission logic
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )
            messages = Message.objects.filter(
                conversation=conversation
            ).select_related('sender').order_by('sent_at')

            # Check object-level permission for each message (though queryset should handle this)
            for message in messages:
                if not IsParticipantOfConversation().has_object_permission(request, self, message):
                    return Response(
                        {'error': 'Access denied to some messages'},
                        status=status.HTTP_403_FORBIDDEN
                    )

            serializer = MessageSerializer(
                messages, many=True, context={'request': request})
            return Response(serializer.data)

        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
