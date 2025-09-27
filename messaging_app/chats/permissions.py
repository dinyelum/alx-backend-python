# chats/permissions.py
from rest_framework import permissions
from .models import Conversation, Message


class IsParticipantOfConversation(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access messages.
    - Allow only authenticated users to access the API
    - Allow only participants in a conversation to send, view, update and delete messages
    """

    def has_permission(self, request, view):
        """
        Check if the user has permission to access the view (list/create actions)
        """
        # Allow only authenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # For creating messages (POST requests), check if user is participant in the conversation
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

        # For listing messages (GET requests), allow authenticated users
        # The queryset will be filtered to only show conversations they participate in
        return True

    def has_object_permission(self, request, view, obj):
        """
        Check if the user has permission to access a specific message object
        """
        # Allow only authenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # For message objects, check if user is participant in the conversation
        if isinstance(obj, Message):
            return obj.conversation.participants.filter(user_id=request.user.user_id).exists()

        # For conversation objects, check if user is a participant
        if isinstance(obj, Conversation):
            return obj.participants.filter(user_id=request.user.user_id).exists()

        return False


class IsMessageOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a message to update or delete it.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any participant
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions (update/delete) only allowed to the message owner
        return obj.sender == request.user


class IsAuthenticatedAndReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow authenticated users to read data.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
