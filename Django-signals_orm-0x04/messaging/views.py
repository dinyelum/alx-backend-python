# messaging/views.py
from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch, Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from .models import Conversation, Message, Notification, MessageHistory
from .serializers import (
    ConversationSerializer,
    ConversationDetailSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    UserSerializer
)
from .permissions import IsParticipantOfConversation, IsMessageOwner
from .pagination import MessagePagination, ConversationPagination
from .filters import MessageFilter, ConversationFilter

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for user management, including account deletion
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        # Users can only access their own account
        return User.objects.filter(user_id=self.request.user.user_id)

    @action(detail=False, methods=['post'])
    def delete_account(self, request):
        """
        Custom action to allow users to delete their own account
        """
        user = request.user

        # You might want to add additional validation here
        # For example, check if the user has any pending transactions, etc.

        # Log the deletion for audit purposes
        logger.info(f"User {user.email} is deleting their account")

        # Delete the user account
        # The post_delete signal will handle cleanup of related objects
        user.delete()

        return Response(
            {
                "message": "Account successfully deleted. All your data has been removed from our systems."
            },
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def profile(self, request):
        """
        Get current user's profile
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating conversations.
    Users can only see conversations they are participants in.
    """
    permission_classes = [permissions.IsAuthenticated,
                          IsParticipantOfConversation]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['participants__first_name',
                     'participants__last_name', 'participants__email']
    ordering_fields = ['created_at', 'last_message_time']
    ordering = ['-created_at']
    pagination_class = ConversationPagination

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
                'sender').order_by('-timestamp')
        )

        queryset = Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related(
            'participants',
            messages_prefetch
        ).annotate(
            participants_count=Count('participants')
        ).distinct()

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
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['timestamp', 'sender__first_name']
    ordering = ['-timestamp']
    pagination_class = MessagePagination

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
        ).select_related('sender', 'conversation', 'conversation__participants')

        return queryset

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
        Custom action to get all messages for a specific conversation with pagination
        """
        try:
            # Verify user has access to this conversation
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )

            # Apply filtering and pagination
            queryset = Message.objects.filter(
                conversation=conversation
            ).select_related('sender').order_by('-timestamp')

            # Apply filters
            queryset = MessageFilter(request.GET, queryset=queryset).qs

            # Paginate the results
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = MessageSerializer(
                    page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)

            serializer = MessageSerializer(
                queryset, many=True, context={'request': request})
            return Response(serializer.data)

        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
