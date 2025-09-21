# serializers.py
from rest_framework import serializers
from django.db import transaction
from .models import Conversation, Message, User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name', 'email']
        read_only_fields = ['user_id']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    message_body = serializers.CharField(required=True)

    class Meta:
        model = Message
        fields = ['message_id', 'sender', 'message_body', 'sent_at']
        read_only_fields = ['message_id', 'sender', 'sent_at']


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

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants',
                  'participant_ids', 'messages', 'created_at']
        read_only_fields = ['conversation_id', 'created_at']

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
    """Serializer for detailed conversation view with messages"""
    messages = MessageSerializer(many=True, read_only=True)

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields
