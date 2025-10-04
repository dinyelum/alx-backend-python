# messaging/models.py
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser
from django.utils import timezone


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

    class Meta:
        db_table = 'conversation'

    def __str__(self):
        return f"Conversation {self.conversation_id}"


class Message(models.Model):
    message_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages')
    # Add receiver field as requested
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_messages', null=True, blank=True)
    content = models.TextField()  # Changed from message_body to content
    # Changed from sent_at to timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = 'message'
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.email} at {self.timestamp}"

    def save(self, *args, **kwargs):
        # Auto-set receiver if not provided (for one-on-one conversations)
        if not self.receiver and self.conversation:
            # Set receiver to the first other participant in the conversation
            other_participants = self.conversation.participants.exclude(
                user_id=self.sender.user_id)
            if other_participants.exists():
                self.receiver = other_participants.first()
        super().save(*args, **kwargs)


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('system', 'System Notification'),
        ('alert', 'Alert'),
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
    timestamp = models.DateTimeField(
        auto_now_add=True)  # Added timestamp field

    class Meta:
        db_table = 'notification'
        ordering = ['-timestamp']

    def __str__(self):
        return f"Notification for {self.user.email}: {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.save()
