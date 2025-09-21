from django.shortcuts import render
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Conversation, Message, User
from .serializers import ConversationSerializer, MessageSerializer, MessageCreateSerializer

# Create your views here.


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating conversations.
    Users can only see conversations they are participants in.
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return only conversations where the current user is a participant
        """
        return Conversation.objects.filter(participants=self.request.user).prefetch_related('participants', 'messages__sender')

    def perform_create(self, serializer):
        """
        Automatically add the current user as a participant when creating a conversation
        """
        conversation = serializer.save()
        conversation.participants.add(self.request.user)

        # Add other participants if provided
        participant_ids = self.request.data.get('participant_ids', [])
        if participant_ids:
            try:
                participants = User.objects.filter(user_id__in=participant_ids)
                conversation.participants.add(*participants)
            except (ValueError, TypeError):
                # Handle invalid UUID format
                pass

    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """
        Custom action to add a participant to an existing conversation
        """
        conversation = self.get_object()
        participant_id = request.data.get('participant_id')

        if not participant_id:
            return Response(
                {'error': 'participant_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            participant = User.objects.get(user_id=participant_id)
            conversation.participants.add(participant)
            return Response(
                {'status': 'participant added'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Invalid user ID format'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for listing, retrieving, and creating messages.
    Users can only see messages from conversations they are participants in.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return only messages from conversations where the current user is a participant
        """
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related('sender', 'conversation')

    def get_serializer_class(self):
        """
        Use different serializers for different actions
        """
        if self.action in ['create', 'update', 'partial_update']:
            return MessageCreateSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        """
        Automatically set the current user as the sender when creating a message
        """
        serializer.save(sender=self.request.user)

    @action(detail=False, methods=['get'], url_path='conversation/(?P<conversation_id>[^/.]+)')
    def conversation_messages(self, request, conversation_id=None):
        """
        Custom action to get all messages for a specific conversation
        """
        try:
            # Verify user has access to this conversation
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )
            messages = Message.objects.filter(
                conversation=conversation
            ).select_related('sender').order_by('sent_at')

            serializer = self.get_serializer(messages, many=True)
            return Response(serializer.data)

        except Conversation.DoesNotExist:
            return Response(
                {'error': 'Conversation not found or access denied'},
                status=status.HTTP_404_NOT_FOUND
            )
