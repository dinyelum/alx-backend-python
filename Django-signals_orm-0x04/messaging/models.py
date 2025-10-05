# messaging/models.py
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone
from django.db.models import Q


class User(AbstractBaseUser):
    user_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=10, choices=[
        ('guest', 'Guest'),
        ('host', 'Host'),
        ('admin', 'Admin')
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'user'

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"


class Conversation(models.Model):
    conversation_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)  # Track last activity

    class Meta:
        db_table = 'conversation'

    def __str__(self):
        return f"Conversation {self.conversation_id}"

    def update_last_activity(self):
        """Update the last_activity timestamp"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])


class Message(models.Model):
    message_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)

    # Self-referential foreign key for threaded replies
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True,
        verbose_name="Parent Message"
    )

    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'message'
        ordering = ['timestamp']
        indexes = [
            models.Index(
                fields=['conversation', 'parent_message', 'timestamp']),
            models.Index(fields=['parent_message']),
        ]

    def __str__(self):
        thread_info = f" (reply to {self.parent_message.message_id})" if self.parent_message else ""
        edited_indicator = " (edited)" if self.edited else ""
        return f"Message from {self.sender.email} at {self.timestamp}{thread_info}{edited_indicator}"

    def save(self, *args, **kwargs):
        # Auto-set receiver if not provided (for one-on-one conversations)
        if not self.receiver and self.conversation:
            other_participants = self.conversation.participants.exclude(
                user_id=self.sender.user_id)
            if other_participants.exists():
                self.receiver = other_participants.first()

        # Update conversation last activity
        if self.conversation:
            self.conversation.update_last_activity()

        super().save(*args, **kwargs)

    @property
    def is_reply(self):
        """Check if this message is a reply"""
        return self.parent_message is not None

    @property
    def reply_count(self):
        """Get the number of replies to this message"""
        return self.replies.count()

    def get_thread_depth(self):
        """Calculate the depth of this message in the thread"""
        depth = 0
        current = self
        while current.parent_message:
            depth += 1
            current = current.parent_message
            if depth > 100:  # Safety limit to prevent infinite loops
                break
        return depth


class MessageHistory(models.Model):
    """
    Model to store historical versions of edited messages
    """
    history_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='history')
    old_content = models.TextField()
    new_content = models.TextField()
    edited_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='message_edits')
    edited_at = models.DateTimeField(auto_now_add=True)
    version_number = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'message_history'
        ordering = ['-edited_at']
        verbose_name_plural = 'Message histories'

    def __str__(self):
        return f"History v{self.version_number} for Message {self.message.message_id}"


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('system', 'System Notification'),
        ('alert', 'Alert'),
        ('edit', 'Message Edited'),
        ('reply', 'Message Reply'),
    ]

    notification_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications')
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    notification_type = models.CharField(
        max_length=20, choices=NOTIFICATION_TYPES, default='message')
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notification'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save()

# Custom managers for optimized queries


class ThreadedMessageManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related(
            'sender',
            'receiver',
            'parent_message',
            'parent_message__sender'
        ).prefetch_related('replies')

    def get_conversation_threads(self, conversation_id):
        """
        Get all root messages (non-replies) in a conversation with their reply threads
        """
        from django.db.models import Prefetch

        # Prefetch replies recursively (up to a certain depth)
        replies_prefetch = Prefetch(
            'replies',
            queryset=Message.objects.select_related('sender', 'receiver').prefetch_related(
                Prefetch('replies', queryset=Message.objects.select_related(
                    'sender', 'receiver'))
            )
        )

        return self.filter(
            conversation_id=conversation_id,
            parent_message__isnull=True  # Root messages only
        ).prefetch_related(replies_prefetch).order_by('timestamp')

    def get_message_with_thread(self, message_id):
        """
        Get a specific message with its entire reply thread
        """
        from django.db.models import Prefetch

        # Prefetch all replies recursively
        def get_replies_prefetch():
            return Prefetch(
                'replies',
                queryset=Message.objects.select_related('sender', 'receiver').prefetch_related(
                    get_replies_prefetch()
                )
            )

        return self.select_related(
            'sender', 'receiver', 'parent_message', 'parent_message__sender'
        ).prefetch_related(
            get_replies_prefetch()
        ).get(message_id=message_id)


# Attach the custom manager to Message model
Message.objects = ThreadedMessageManager()
