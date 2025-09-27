# chats/permissions.py
from rest_framework import permissions
from .models import Conversation, Message


class IsParticipant(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access it.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the user is a participant in the conversation
        if isinstance(obj, Conversation):
            return obj.participants.filter(user_id=request.user.user_id).exists()
        return False


class IsMessageParticipant(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access messages.
    """

    def has_object_permission(self, request, view, obj):
        # Check if the user is a participant in the message's conversation
        if isinstance(obj, Message):
            return obj.conversation.participants.filter(user_id=request.user.user_id).exists()
        return False


class IsOwnerOrParticipant(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or participants to edit it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any participant,
        # write permissions are only allowed to the owner of the message
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'conversation'):
                return obj.conversation.participants.filter(user_id=request.user.user_id).exists()
            elif hasattr(obj, 'participants'):
                return obj.participants.filter(user_id=request.user.user_id).exists()

        # Write permissions only for the owner
        if hasattr(obj, 'sender'):
            return obj.sender == request.user

        return False


class CanSendMessage(permissions.BasePermission):
    """
    Custom permission to check if user can send a message to a conversation.
    """

    def has_permission(self, request, view):
        if request.method == 'POST':
            # For message creation, check if user is participant in the conversation
            conversation_id = request.data.get('conversation')
            if conversation_id:
                from .models import Conversation
                try:
                    conversation = Conversation.objects.get(
                        conversation_id=conversation_id)
                    return conversation.participants.filter(user_id=request.user.user_id).exists()
                except Conversation.DoesNotExist:
                    return False
        return True
