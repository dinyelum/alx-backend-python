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

    def test_message_creation_triggers_notification(self):
        """Test that creating a message triggers notifications for other participants"""
        # Count initial notifications
        initial_notification_count = Notification.objects.count()

        # Create a message from user1
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_body="Hello everyone!"
        )

        # Check that notifications were created for user2 and user3 (but not user1)
        final_notification_count = Notification.objects.count()
        self.assertEqual(final_notification_count -
                         initial_notification_count, 2)

        # Verify notifications are for the correct users
        user2_notifications = Notification.objects.filter(
            user=self.user2, message=message)
        user3_notifications = Notification.objects.filter(
            user=self.user3, message=message)
        user1_notifications = Notification.objects.filter(
            user=self.user1, message=message)

        self.assertEqual(user2_notifications.count(), 1)
        self.assertEqual(user3_notifications.count(), 1)
        self.assertEqual(user1_notifications.count(), 0)

        # Verify notification content
        notification = user2_notifications.first()
        self.assertEqual(notification.notification_type, 'message')
        self.assertIn(self.user1.first_name, notification.title)
        self.assertIn(message.message_body, notification.content)
        self.assertFalse(notification.is_read)

    def test_notification_creation_for_single_participant(self):
        """Test notification creation in a two-person conversation"""
        # Create a conversation with only two participants
        conversation2 = Conversation.objects.create()
        conversation2.participants.add(self.user1, self.user2)

        initial_notification_count = Notification.objects.count()

        # User1 sends message
        message = Message.objects.create(
            conversation=conversation2,
            sender=self.user1,
            message_body="Hello user2!"
        )

        # Should create one notification for user2
        final_notification_count = Notification.objects.count()
        self.assertEqual(final_notification_count -
                         initial_notification_count, 1)

        notification = Notification.objects.filter(user=self.user2).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.message, message)

    def test_no_notification_for_sender(self):
        """Test that the message sender doesn't receive a notification"""
        conversation2 = Conversation.objects.create()
        conversation2.participants.add(self.user1, self.user2)

        # User1 sends message
        message = Message.objects.create(
            conversation=conversation2,
            sender=self.user1,
            message_body="Test message"
        )

        # Check that user1 (sender) didn't get a notification
        user1_notifications = Notification.objects.filter(
            user=self.user1, message=message)
        self.assertEqual(user1_notifications.count(), 0)

    def test_notification_content_truncation(self):
        """Test that long message content is properly truncated in notifications"""
        long_message = "This is a very long message that should be truncated in the notification. " * 5

        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_body=long_message
        )

        notification = Notification.objects.filter(user=self.user2).first()
        self.assertIsNotNone(notification)
        self.assertTrue(len(notification.content) <= 103)  # 100 chars + "..."
        self.assertTrue(notification.content.endswith('...'))

    def test_message_update_does_not_trigger_notification(self):
        """Test that updating a message doesn't trigger new notifications"""
        message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            message_body="Original message"
        )

        # Clear initial notifications
        Notification.objects.all().delete()
        initial_notification_count = Notification.objects.count()

        # Update the message
        message.message_body = "Updated message"
        message.save()

        # No new notifications should be created
        final_notification_count = Notification.objects.count()
        self.assertEqual(final_notification_count, initial_notification_count)


class NotificationModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@test.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )

    def test_notification_creation(self):
        """Test basic notification creation"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='system',
            title='System Update',
            content='The system will be updated tonight.'
        )

        self.assertIsNotNone(notification.notification_id)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'system')
        self.assertFalse(notification.is_read)

    def test_notification_mark_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            content='Test content'
        )

        self.assertFalse(notification.is_read)
        notification.mark_as_read()
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_notification_ordering(self):
        """Test that notifications are ordered by creation date (newest first)"""
        notification1 = Notification.objects.create(
            user=self.user,
            title='First Notification',
            content='First content'
        )

        notification2 = Notification.objects.create(
            user=self.user,
            title='Second Notification',
            content='Second content'
        )

        notifications = Notification.objects.all()
        self.assertEqual(notifications[0], notification2)
        self.assertEqual(notifications[1], notification1)
