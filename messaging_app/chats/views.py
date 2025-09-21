# views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch
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

        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related(
            'participants',
            messages_prefetch
        ).distinct()

    def perform_create(self, serializer):
        # Creation is handled in the serializer's create method
        serializer.save()

    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

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

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MessageCreateSerializer
        return MessageSerializer

    def get_queryset(self):
        """
        Return only messages from conversations where the current user is a participant
        """
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related('sender', 'conversation').order_by('-sent_at')

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
            response_serializer = MessageSerializer(message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
