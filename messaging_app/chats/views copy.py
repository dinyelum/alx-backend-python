# views.py
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


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating conversations.
    Users can only see conversations they are participants in.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter,
                       filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['participants__first_name',
                     'participants__last_name', 'participants__email']
    ordering_fields = ['created_at', 'last_message_time']
    ordering = ['-created_at']
    filterset_fields = ['participants__user_id']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    def get_queryset(self):
        """
        Return only conversations where the current user is a participant
        Prefetch messages with sender information for efficient nested serialization
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

        # Additional filtering based on query parameters
        participant_filter = self.request.query_params.get('participant')
        if participant_filter:
            queryset = queryset.filter(
                participants__user_id=participant_filter)

        return queryset

    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        # Creation is handled in the serializer's create method
        serializer.save()

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get all messages for a specific conversation"""
        conversation = self.get_object()
        messages = Message.objects.filter(
            conversation=conversation
        ).select_related('sender').order_by('sent_at')

        serializer = MessageSerializer(
            messages, many=True, context={'request': request})
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating messages.
    Users can only see messages from conversations they are participants in.
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter,
                       filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['message_body', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['sent_at', 'sender__first_name']
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

        # Additional filtering based on query parameters
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
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        """Automatically set the current user as the sender"""
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['post'])
    def send_message(self, request):
        """Alternative endpoint specifically for sending messages"""
        serializer = MessageCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            message = serializer.save(sender=request.user)
            response_serializer = MessageSerializer(
                message, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Custom search endpoint for messages"""
        search_term = request.query_params.get('q')
        if not search_term:
            return Response(
                {'error': 'Search term (q) is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        messages = Message.objects.filter(
            Q(message_body__icontains=search_term) &
            Q(conversation__participants=request.user)
        ).select_related('sender', 'conversation').order_by('-sent_at')

        serializer = MessageSerializer(
            messages, many=True, context={'request': request})
        return Response(serializer.data)
