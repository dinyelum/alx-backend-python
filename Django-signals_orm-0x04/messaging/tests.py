# messaging/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Conversation, Message, Notification
import uuid


class NotificationSignalTests(TestCase):
    def setUp(self):
        # Create test users
        self.user1 = get_user_model().objects.create_user(
            email='user1@test.com',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.user2 = get_user_model().objects.create_user(
            email='user2@test.com',
            first_name='Jane',
            last_name='Smith',
            password='testpass123'
        )
        self.user3 = get_user_model().objects.create_user(
            email='user3@test.com',
            first_name='Bob',
            last_name='Johnson',
            password='testpass123'
        )

        # Create conversation
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2, self.user3)

    def test_message_with_receiver_field(self):
        """Test that Message model has receiver field"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,  # Explicit receiver
            content="Hello Jane!"
        )

        self.assertEqual(message.receiver, self.user2)
        self.assertEqual(message.content, "Hello Jane!")
        self.assertIsNotNone(message.timestamp)

    def test_message_auto_sets_receiver(self):
        """Test that receiver is auto-set for one-on-one conversations"""
        # Create one-on-one conversation
        conversation2 = Conversation.objects.create()
        conversation2.participants.add(self.user1, self.user2)

        message = Message.objects.create(
            conversation=conversation2,
            sender=self.user1,
            content="Auto-set receiver test"
        )

        # Receiver should be auto-set to user2
        self.assertEqual(message.receiver, self.user2)

    def test_message_creation_with_timestamp(self):
        """Test that message has timestamp field"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Test message with timestamp"
        )

        self.assertIsNotNone(message.timestamp)
        self.assertEqual(message.content, "Test message with timestamp")

    def test_notification_creation_for_receiver(self):
        """Test that notification is created for specific receiver"""
        initial_notification_count = Notification.objects.count()

        # Create message with specific receiver
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,  # Only user2 should get notification
            content="Direct message to Jane"
        )

        # Check that only one notification was created (for user2)
        final_notification_count = Notification.objects.count()
        self.assertEqual(final_notification_count -
                         initial_notification_count, 1)

        # Verify notification is for user2 only
        user2_notifications = Notification.objects.filter(
            user=self.user2, message=message)
        user3_notifications = Notification.objects.filter(
            user=self.user3, message=message)

        self.assertEqual(user2_notifications.count(), 1)
        self.assertEqual(user3_notifications.count(), 0)

        # Verify notification content
        notification = user2_notifications.first()
        self.assertEqual(notification.notification_type, 'message')
        self.assertIn(self.user1.first_name, notification.title)
        self.assertIn(message.content, notification.content)
        self.assertIsNotNone(notification.timestamp)


class MessageModelTests(TestCase):
    def setUp(self):
        self.user1 = get_user_model().objects.create_user(
            email='sender@test.com',
            first_name='Sender',
            last_name='User',
            password='testpass123'
        )
        self.user2 = get_user_model().objects.create_user(
            email='receiver@test.com',
            first_name='Receiver',
            last_name='User',
            password='testpass123'
        )

        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)

    def test_message_fields_exist(self):
        """Test that Message model has all required fields"""
        message = Message(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Test message content",
        )

        # Check that all required fields are present
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.receiver, self.user2)
        self.assertEqual(message.content, "Test message content")
        self.assertIsNotNone(message.timestamp)

    def test_message_string_representation(self):
        """Test Message string representation"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Test message"
        )

        self.assertIn(self.user1.email, str(message))
        self.assertIn("Message from", str(message))
