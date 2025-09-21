# serializers.py
from rest_framework import serializers
from django.db import transaction
from .models import Conversation, Message, User


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name', 'full_name', 'email']
        read_only_fields = ['user_id']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    message_body = serializers.CharField(required=True)
    is_own_message = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['message_id', 'sender',
                  'message_body', 'sent_at', 'is_own_message']
        read_only_fields = ['message_id',
                            'sender', 'sent_at', 'is_own_message']

    def get_is_own_message(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender.user_id == request.user.user_id
        return False


class MessageCreateSerializer(serializers.ModelSerializer):
    message_body = serializers.CharField(required=True, max_length=5000)

    class Meta:
        model = Message
        fields = ['conversation', 'message_body']

    def validate_conversation(self, value):
        user = self.context['request'].user
        if not value.participants.filter(user_id=user.user_id).exists():
            raise serializers.ValidationError(
                "You are not a participant in this conversation")
        return value


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=True,
        allow_empty=False
    )
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'participants', 'participant_ids', 'messages',
            'unread_count', 'last_message', 'created_at'
        ]
        read_only_fields = ['conversation_id', 'created_at']

    def get_unread_count(self, obj):
        # Example implementation - you might want to track read status in your model
        request = self.context.get('request')
        if request and request.user:
            # This is a placeholder - implement your own read/unread logic
            return 0
        return 0

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            # Pass context to the nested serializer
            message_serializer = MessageSerializer(
                last_message, context=self.context)
            return message_serializer.data
        return None

    def validate_participant_ids(self, value):
        if len(value) < 1:
            raise serializers.ValidationError(
                "At least one participant is required")

        # Check if all participant IDs are valid users
        valid_users = User.objects.filter(
            user_id__in=value).values_list('user_id', flat=True)
        invalid_ids = set(value) - set(valid_users)

        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid user IDs: {invalid_ids}")

        return value

    @transaction.atomic
    def create(self, validated_data):
        participant_ids = validated_data.pop('participant_ids')
        conversation = Conversation.objects.create(**validated_data)

        # Add all participants including the current user
        participants = User.objects.filter(user_id__in=participant_ids)
        conversation.participants.add(*participants)

        # Always add the current user as a participant
        current_user = self.context['request'].user
        if current_user.user_id not in participant_ids:
            conversation.participants.add(current_user)

        return conversation


class ConversationDetailSerializer(ConversationSerializer):
    """Serializer for detailed conversation view with all messages"""
    messages = serializers.SerializerMethodField()

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields

    def get_messages(self, obj):
        # Get all messages ordered by sent_at
        messages = obj.messages.all().select_related('sender').order_by('sent_at')
        serializer = MessageSerializer(
            messages, many=True, context=self.context)
        return serializer.data
