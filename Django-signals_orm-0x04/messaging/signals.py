# messaging/signals.py
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from .models import Message, Notification, User, Conversation, MessageHistory
import logging

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=User)
def cleanup_user_data(sender, instance, **kwargs):
    """
    Signal to automatically clean up all related data when a user is deleted.
    This handles data that isn't automatically deleted by CASCADE constraints.
    """
    try:
        user_id = instance.user_id
        logger.info(
            f"Cleaning up data for deleted user: {instance.email} ({user_id})")

        # 1. Clean up conversations where this user was the only participant
        # First, get all conversations where this user was a participant
        user_conversations = Conversation.objects.filter(participants=instance)

        for conversation in user_conversations:
            remaining_participants = conversation.participants.exclude(
                user_id=user_id)

            if remaining_participants.count() == 0:
                # No participants left, delete the conversation
                logger.info(
                    f"Deleting empty conversation {conversation.conversation_id}")
                conversation.delete()
            else:
                # Remove user from conversation participants
                conversation.participants.remove(instance)
                logger.info(
                    f"Removed user from conversation {conversation.conversation_id}")

        # 2. Clean up notifications for this user
        # Notifications should be deleted via CASCADE, but we'll log it
        notification_count = Notification.objects.filter(user=instance).count()
        if notification_count > 0:
            logger.info(
                f"Deleting {notification_count} notifications for user {user_id}")
            # These should be deleted by CASCADE, but we explicitly check

        # 3. Clean up MessageHistory where this user was the editor
        message_history_count = MessageHistory.objects.filter(
            edited_by=instance).count()
        if message_history_count > 0:
            logger.info(
                f"Deleting {message_history_count} message history entries for user {user_id}")
            # Update edited_by to NULL or system user if you want to preserve history
            # For now, we'll let CASCADE handle it if set up, or delete explicitly:
            MessageHistory.objects.filter(edited_by=instance).delete()

        # 4. Handle messages where this user was the sender or receiver
        # Update sender/receiver to NULL to preserve message history in conversations
        sent_messages_count = Message.objects.filter(sender=instance).count()
        received_messages_count = Message.objects.filter(
            receiver=instance).count()

        if sent_messages_count > 0:
            logger.info(
                f"Updating {sent_messages_count} messages where user was sender")
            Message.objects.filter(sender=instance).update(
                sender=None,
                content="[Message deleted - user account removed]"
            )

        if received_messages_count > 0:
            logger.info(
                f"Updating {received_messages_count} messages where user was receiver")
            Message.objects.filter(receiver=instance).update(receiver=None)

        logger.info(f"Successfully cleaned up data for deleted user {user_id}")

    except Exception as e:
        logger.error(
            f"Error cleaning up data for deleted user {instance.user_id}: {str(e)}")


@receiver(pre_save, sender=Message)
def track_message_edits(sender, instance, **kwargs):
    """
    Signal to log the old content of a message before it's updated.
    Creates a MessageHistory entry when a message is edited.
    """
    if instance.pk:  # Only for existing messages (updates, not creations)
        try:
            # Get the original message from database
            original = Message.objects.get(pk=instance.pk)

            # Check if content has changed
            if original.content != instance.content:
                # Get the latest version number
                latest_version = MessageHistory.objects.filter(
                    message=instance
                ).order_by('-version_number').first()

                version_number = 1
                if latest_version:
                    version_number = latest_version.version_number + 1

                # Explicitly use MessageHistory.objects.create as required
                MessageHistory.objects.create(
                    message=instance,
                    old_content=original.content,
                    new_content=instance.content,
                    edited_by=instance.sender,  # Assuming the sender is editing
                    version_number=version_number
                )

                # Update message edited fields
                instance.edited = True
                instance.edited_at = timezone.now()

                logger.info(
                    f"Message {instance.message_id} edited. Version {version_number} saved.")

                # Create notification for message edit (optional)
                create_edit_notification(instance, original.content)

        except Message.DoesNotExist:
            logger.warning(
                f"Original message not found for {instance.message_id}")
        except Exception as e:
            logger.error(
                f"Error tracking message edit for {instance.message_id}: {str(e)}")


def create_edit_notification(message, old_content):
    """
    Create notification when a message is edited
    """
    try:
        # Notify all participants in the conversation except the editor
        participants = message.conversation.participants.exclude(
            user_id=message.sender.user_id)

        for participant in participants:
            # Use Notification.objects.create explicitly
            Notification.objects.create(
                user=participant,
                message=message,
                notification_type='edit',
                title=f"Message edited by {message.sender.first_name}",
                content=f"Message was updated: '{old_content[:50]}...' → '{message.content[:50]}...'"
            )

            logger.info(f"Edit notification created for {participant.email}")

    except Exception as e:
        logger.error(f"Error creating edit notification: {str(e)}")


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal to create notifications for the receiver when a new message is created.
    """
    if created:
        try:
            # Use the receiver field if specified, otherwise notify all other participants
            if instance.receiver:
                receivers = [instance.receiver]
            else:
                conversation = instance.conversation
                receivers = conversation.participants.exclude(
                    user_id=instance.sender.user_id)

            for receiver_user in receivers:
                # Use Notification.objects.create explicitly
                Notification.objects.create(
                    user=receiver_user,
                    message=instance,
                    notification_type='message',
                    title=f"New message from {instance.sender.first_name} {instance.sender.last_name}",
                    content=f"{instance.content[:100]}..." if len(
                        instance.content) > 100 else instance.content
                )

                logger.info(
                    f"Notification created for user {receiver_user.email}")

        except Exception as e:
            logger.error(
                f"Error creating notification for message {instance.message_id}: {str(e)}")


@receiver(pre_save, sender=Message)
def set_receiver_if_not_provided(sender, instance, **kwargs):
    """
    Automatically set receiver for one-on-one conversations if not provided.
    """
    if not instance.receiver and instance.conversation and instance.sender:
        try:
            other_participants = instance.conversation.participants.exclude(
                user_id=instance.sender.user_id)
            if other_participants.count() == 1:
                instance.receiver = other_participants.first()
        except Exception as e:
            logger.error(f"Error setting receiver for message: {str(e)}")
