# messaging/serializers.py
from rest_framework import serializers
from .models import User, Conversation, Message, Notification, MessageHistory


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['user_id', 'first_name', 'last_name', 'email']
        read_only_fields = ['user_id']


class MessageHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageHistory
        fields = ['history_id', 'old_content', 'new_content',
                  'edited_by', 'edited_at', 'version_number']
        read_only_fields = ['history_id', 'edited_at']


class ThreadedMessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    reply_count = serializers.ReadOnlyField()
    is_reply = serializers.ReadOnlyField()
    thread_depth = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'receiver', 'content', 'timestamp',
            'is_read', 'edited', 'edited_at', 'parent_message', 'replies',
            'reply_count', 'is_reply', 'thread_depth'
        ]
        read_only_fields = ['message_id', 'timestamp', 'edited', 'edited_at']

    def get_replies(self, obj):
        """
        Recursively serialize replies using the same serializer
        """
        # Limit recursion depth to prevent infinite loops
        max_depth = self.context.get('max_depth', 3)
        current_depth = self.context.get('current_depth', 0)

        if current_depth >= max_depth:
            return []

        replies = obj.replies.all().order_by('timestamp')
        context = self.context.copy()
        context['current_depth'] = current_depth + 1

        return ThreadedMessageSerializer(replies, many=True, context=context).data

    def get_thread_depth(self, obj):
        return obj.get_thread_depth()


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['conversation', 'content', 'parent_message']

    def validate_parent_message(self, value):
        """
        Validate that the parent message exists and is in the same conversation
        """
        if value:
            conversation = self.initial_data.get('conversation')
            if conversation and value.conversation_id != conversation:
                raise serializers.ValidationError(
                    "Parent message must be in the same conversation")
        return value


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['conversation_id', 'participants', 'last_message',
                  'unread_count', 'created_at', 'last_activity']
        read_only_fields = ['conversation_id', 'created_at', 'last_activity']

    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-timestamp').first()
        if last_message:
            return ThreadedMessageSerializer(last_message).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0


class ConversationDetailSerializer(ConversationSerializer):
    messages = serializers.SerializerMethodField()

    class Meta(ConversationSerializer.Meta):
        fields = ConversationSerializer.Meta.fields + ['messages']

    def get_messages(self, obj):
        """
        Get root messages (non-replies) with their threaded replies
        """
        root_messages = obj.messages.filter(
            parent_message__isnull=True).order_by('timestamp')
        return ThreadedMessageSerializer(root_messages, many=True, context=self.context).data


class NotificationSerializer(serializers.ModelSerializer):
    message = ThreadedMessageSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['notification_id', 'user', 'message',
                  'notification_type', 'title', 'content', 'is_read', 'timestamp']
        read_only_fields = ['notification_id', 'timestamp']
