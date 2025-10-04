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
    sender = models.ForeignKey(User, on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='sent_messages')
    receiver = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_messages')
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    # New field to track if message has been edited
    edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'message'
        ordering = ['timestamp']

    def __str__(self):
        edited_indicator = " (edited)" if self.edited else ""
        return f"Message from {self.sender.email} at {self.timestamp}{edited_indicator}"

    def save(self, *args, **kwargs):
        # Auto-set receiver if not provided (for one-on-one conversations)
        if not self.receiver and self.conversation:
            other_participants = self.conversation.participants.exclude(
                user_id=self.sender.user_id)
            if other_participants.exists():
                self.receiver = other_participants.first()
        super().save(*args, **kwargs)


class MessageHistory(models.Model):
    """
    Model to store historical versions of edited messages
    """
    history_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='history')
    edited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='message_edits')
    old_content = models.TextField()
    new_content = models.TextField()
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
    ]

    notification_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications')
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name='notifications')
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
