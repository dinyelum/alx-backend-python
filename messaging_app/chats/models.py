from django.db import models
import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.


class UserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name,
                          last_name=last_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        return self.create_user(email, first_name, last_name, password, **extra_fields)


class User(AbstractBaseUser):
    class Role(models.TextChoices):
        GUEST = 'guest', 'Guest'
        HOST = 'host', 'Host'
        ADMIN = 'admin', 'Admin'

    user_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    first_name = models.CharField(max_length=255, null=False)
    last_name = models.CharField(max_length=255, null=False)
    email = models.EmailField(unique=True, null=False)
    password_hash = models.CharField(max_length=255, null=False)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    role = models.CharField(max_length=10, choices=Role.choices, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'user'
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    @property
    def is_authenticated(self):
        return True

    # Add these methods for JWT compatibility
    def get_username(self):
        return self.email

    def __str__(self):
        return self.email


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
    receiver = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_messages')
    message_body = models.TextField(null=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message'
        ordering = ['sent_at']

    def __str__(self):
        return f"Message from {self.sender.email} at {self.sent_at}"

# Additional models mentioned in constraints (for completeness)


class Property(models.Model):
    property_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    host = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='properties')
    # Add other property fields as needed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'property'


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        CANCELED = 'canceled', 'Canceled'

    booking_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'booking'


class Payment(models.Model):
    payment_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name='payments')
    # Add payment fields as needed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment'


class Review(models.Model):
    review_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, db_index=True)
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)])
    # Add review content field as needed
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'review'
        constraints = [
            models.UniqueConstraint(
                fields=['property', 'user'], name='unique_property_user_review')
        ]
