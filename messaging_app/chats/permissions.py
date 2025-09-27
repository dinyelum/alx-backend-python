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

        # For PUT, PATCH, DELETE methods - check object-level permission in has_object_permission
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            # We'll handle these in has_object_permission
            return True

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
            is_participant = obj.conversation.participants.filter(
                user_id=request.user.user_id).exists()

            # Explicitly check for PUT, PATCH, DELETE methods
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                # For update/delete, user must be both participant AND message owner
                return is_participant and obj.sender == request.user

            # For GET (view) and other safe methods, just need to be participant
            if request.method in permissions.SAFE_METHODS:
                return is_participant

            # For any other methods, default to participant check
            return is_participant

        # For conversation objects, check if user is a participant
        if isinstance(obj, Conversation):
            is_participant = obj.participants.filter(
                user_id=request.user.user_id).exists()

            # Explicitly check for PUT, PATCH, DELETE methods
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                return is_participant  # Participants can modify conversation details

            # For GET and other safe methods
            if request.method in permissions.SAFE_METHODS:
                return is_participant

            return is_participant

        return False


class IsMessageOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a message to update or delete it.
    Explicitly checks PUT, PATCH, DELETE methods.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any participant (handled by IsParticipantOfConversation)
        if request.method in permissions.SAFE_METHODS:
            return True

        # Explicitly check PUT, PATCH, DELETE methods
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            return obj.sender == request.user

        return False


class CanSendMessage(permissions.BasePermission):
    """
    Custom permission to check if user can send a message to a conversation.
    Explicitly checks POST method.
    """

    def has_permission(self, request, view):
        if request.method == 'POST':
            conversation_id = request.data.get('conversation')
            if conversation_id:
                try:
                    conversation = Conversation.objects.get(
                        conversation_id=conversation_id)
                    return conversation.participants.filter(user_id=request.user.user_id).exists()
                except Conversation.DoesNotExist:
                    return False
        return True

# Alternative version with explicit method checking


class ExplicitMethodPermission(permissions.BasePermission):
    """
    Permission class that explicitly checks all HTTP methods
    """

    def has_object_permission(self, request, view, obj):
        # Allow only authenticated users
        if not request.user or not request.user.is_authenticated:
            return False

        # Check if user is participant in the conversation
        if hasattr(obj, 'conversation'):
            is_participant = obj.conversation.participants.filter(
                user_id=request.user.user_id).exists()
        elif hasattr(obj, 'participants'):
            is_participant = obj.participants.filter(
                user_id=request.user.user_id).exists()
        else:
            return False

        # Explicit method checks
        if request.method == 'GET':
            return is_participant  # View permission

        elif request.method == 'POST':
            return is_participant  # Send permission

        elif request.method in ['PUT', 'PATCH']:
            # For messages, check if user is owner; for conversations, just participant
            if hasattr(obj, 'sender'):
                return is_participant and obj.sender == request.user
            return is_participant

        elif request.method == 'DELETE':
            # For messages, check if user is owner; for conversations, just participant
            if hasattr(obj, 'sender'):
                return is_participant and obj.sender == request.user
            return is_participant

        return False
