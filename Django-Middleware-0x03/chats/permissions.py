# chats/permissions.py
from rest_framework import permissions
from .models import Conversation, Message


class IsParticipantOfConversation(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access messages.
    """

    def has_permission(self, request, view):
        # Allow only authenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # For creating messages (POST requests)
        if request.method == 'POST':
            conversation_id = request.data.get('conversation')
            if conversation_id:
                try:
                    conversation = Conversation.objects.get(
                        conversation_id=conversation_id)
                    return conversation.participants.filter(user_id=request.user.user_id).exists()
                except Conversation.DoesNotExist:
                    return False
            return False

        return True

    def has_object_permission(self, request, view, obj):
        # Allow only authenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is participant
        if isinstance(obj, Message):
            is_participant = obj.conversation.participants.filter(
                user_id=request.user.user_id).exists()
        elif isinstance(obj, Conversation):
            is_participant = obj.participants.filter(
                user_id=request.user.user_id).exists()
        else:
            return False

        # Handle different HTTP methods
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if isinstance(obj, Message):
                return is_participant and obj.sender == request.user
            return is_participant

        return is_participant
