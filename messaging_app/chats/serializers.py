# serializers.py
from rest_framework import serializers
from .models import User, Conversation, Message


class UserSerializer(serializers.ModelSerializer):
    # Read-only field to display full name
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name', 'full_name', 'email',
                  'phone_number', 'role', 'created_at']
        read_only_fields = ['user_id', 'created_at']
        extra_kwargs = {
            # Never expose password hash in responses
            'password_hash': {'write_only': True}
        }

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class MessageSerializer(serializers.ModelSerializer):
    # Nested serializer for sender details
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['message_id', 'sender', 'message_body', 'sent_at']
        read_only_fields = ['message_id', 'sent_at']


class ConversationSerializer(serializers.ModelSerializer):
    # Nested serializers for participants and messages
    participants = UserSerializer(many=True, read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'participant_ids',
                  'messages', 'created_at']
        read_only_fields = ['conversation_id', 'created_at']

    def create(self, validated_data):
        # Extract participant_ids from validated data
        participant_ids = validated_data.pop('participant_ids', [])

        # Create the conversation
        conversation = Conversation.objects.create(**validated_data)

        # Add participants if provided
        if participant_ids:
            participants = User.objects.filter(user_id__in=participant_ids)
            conversation.participants.add(*participants)

        return conversation

    def update(self, instance, validated_data):
        # Handle participant updates
        participant_ids = validated_data.pop('participant_ids', None)

        if participant_ids is not None:
            participants = User.objects.filter(user_id__in=participant_ids)
            instance.participants.set(participants)

        return super().update(instance, validated_data)

# Alternative serializers for different use cases


class SimpleUserSerializer(serializers.ModelSerializer):
    """Simplified user serializer for nested representations"""
    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name', 'email']


class SimpleMessageSerializer(serializers.ModelSerializer):
    """Simplified message serializer for list views"""
    sender = SimpleUserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['message_id', 'sender', 'message_body', 'sent_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """Serializer for listing conversations with basic info"""
    participants = SimpleUserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'last_message',
                  'unread_count', 'created_at']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return SimpleMessageSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        # You can implement your own logic for unread messages
        return 0  # Placeholder


class MessageCreateSerializer(serializers.ModelSerializer):
    """Serializer specifically for creating messages"""
    class Meta:
        model = Message
        fields = ['conversation', 'message_body']

    def create(self, validated_data):
        # Automatically set the sender to the current user
        validated_data['sender'] = self.context['request'].user
        return super().create(validated_data)
