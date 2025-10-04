# messaging/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Conversation, Message, Notification, MessageHistory
from django.utils import timezone
import uuid


class MessageEditHistoryTests(TestCase):
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

        # Create conversation
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)

        # Create initial message
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Original message content"
        )

    def test_message_edited_field(self):
        """Test that Message model has edited field"""
        self.assertFalse(self.message.edited)
        self.assertIsNone(self.message.edited_at)

        # Edit the message
        self.message.content = "Edited message content"
        self.message.save()

        # Refresh from database
        self.message.refresh_from_db()

        # Check that edited fields are updated
        self.assertTrue(self.message.edited)
        self.assertIsNotNone(self.message.edited_at)

    def test_message_history_creation_on_edit(self):
        """Test that MessageHistory is created when message is edited"""
        initial_history_count = MessageHistory.objects.count()

        # Edit the message
        original_content = self.message.content
        new_content = "This is the edited content"
        self.message.content = new_content
        self.message.save()

        # Check that MessageHistory was created
        final_history_count = MessageHistory.objects.count()
        self.assertEqual(final_history_count - initial_history_count, 1)

        # Verify history entry content
        history_entry = MessageHistory.objects.first()
        self.assertEqual(history_entry.message, self.message)
        self.assertEqual(history_entry.old_content, original_content)
        self.assertEqual(history_entry.new_content, new_content)
        self.assertEqual(history_entry.edited_by, self.user1)
        self.assertEqual(history_entry.version_number, 1)

    def test_multiple_edits_create_multiple_history_entries(self):
        """Test that multiple edits create multiple history entries with correct version numbers"""
        # First edit
        self.message.content = "First edit"
        self.message.save()

        # Second edit
        self.message.content = "Second edit"
        self.message.save()

        # Third edit
        self.message.content = "Third edit"
        self.message.save()

        # Check that three history entries were created
        history_entries = MessageHistory.objects.filter(
            message=self.message).order_by('version_number')
        self.assertEqual(history_entries.count(), 3)

        # Verify version numbers
        self.assertEqual(history_entries[0].version_number, 1)
        self.assertEqual(history_entries[1].version_number, 2)
        self.assertEqual(history_entries[2].version_number, 3)

        # Verify content progression
        self.assertEqual(
            history_entries[0].old_content, "Original message content")
        self.assertEqual(history_entries[0].new_content, "First edit")

        self.assertEqual(history_entries[1].old_content, "First edit")
        self.assertEqual(history_entries[1].new_content, "Second edit")

        self.assertEqual(history_entries[2].old_content, "Second edit")
        self.assertEqual(history_entries[2].new_content, "Third edit")

    def test_no_history_created_for_new_messages(self):
        """Test that no history is created for new messages (only updates)"""
        initial_history_count = MessageHistory.objects.count()

        # Create new message (should not create history)
        new_message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            receiver=self.user2,
            content="Brand new message"
        )

        # No history should be created for new messages
        final_history_count = MessageHistory.objects.count()
        self.assertEqual(final_history_count, initial_history_count)

    def test_edit_notification_creation(self):
        """Test that notifications are created when a message is edited"""
        initial_notification_count = Notification.objects.count()

        # Edit the message
        self.message.content = "Edited content"
        self.message.save()

        # Check that notification was created for the other participant
        final_notification_count = Notification.objects.count()
        self.assertEqual(final_notification_count -
                         initial_notification_count, 1)

        # Verify notification details
        notification = Notification.objects.filter(
            notification_type='edit').first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.user, self.user2)
        self.assertEqual(notification.message, self.message)
        self.assertIn("edited", notification.title.lower())
        self.assertIn(self.user1.first_name, notification.title)

    def test_message_string_representation_with_edit(self):
        """Test Message string representation includes edit indicator"""
        # Original message
        self.assertNotIn("(edited)", str(self.message))

        # Edited message
        self.message.content = "Edited content"
        self.message.save()
        self.message.refresh_from_db()

        self.assertIn("(edited)", str(self.message))


class MessageHistoryModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='test@test.com',
            first_name='Test',
            last_name='User',
            password='testpass123'
        )

        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user)

        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user,
            content="Test message"
        )

    def test_message_history_creation(self):
        """Test basic MessageHistory creation"""
        history = MessageHistory.objects.create(
            message=self.message,
            old_content="Old content",
            new_content="New content",
            edited_by=self.user,
            version_number=1
        )

        self.assertIsNotNone(history.history_id)
        self.assertEqual(history.message, self.message)
        self.assertEqual(history.old_content, "Old content")
        self.assertEqual(history.new_content, "New content")
        self.assertEqual(history.edited_by, self.user)
        self.assertEqual(history.version_number, 1)
        self.assertIsNotNone(history.edited_at)

    def test_message_history_ordering(self):
        """Test that MessageHistory entries are ordered by edit time (newest first)"""
        history1 = MessageHistory.objects.create(
            message=self.message,
            old_content="Content v1",
            new_content="Content v2",
            edited_by=self.user,
            version_number=1
        )

        history2 = MessageHistory.objects.create(
            message=self.message,
            old_content="Content v2",
            new_content="Content v3",
            edited_by=self.user,
            version_number=2
        )

        histories = MessageHistory.objects.all()
        self.assertEqual(histories[0], history2)  # Newest first
        self.assertEqual(histories[1], history1)
