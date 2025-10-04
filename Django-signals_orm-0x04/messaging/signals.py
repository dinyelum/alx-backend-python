from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from .models import Message, Notification, User, Conversation
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal to create notifications for all participants in a conversation
    when a new message is created, excluding the sender.
    """
    if created:
        try:
            conversation = instance.conversation
            sender_user = instance.sender

            # Get all participants except the sender
            participants = conversation.participants.exclude(
                user_id=sender_user.user_id)

            for participant in participants:
                # Create notification for each participant
                notification = Notification.objects.create(
                    user=participant,
                    message=instance,
                    notification_type='message',
                    title=f"New message from {sender_user.first_name} {sender_user.last_name}",
                    content=f"{instance.message_body[:100]}..." if len(
                        instance.message_body) > 100 else instance.message_body
                )

                logger.info(
                    f"Notification created for user {participant.email}: {notification.title}")

                # Here you can add additional notification delivery methods:
                # - WebSocket notifications
                # - Email notifications
                # - Push notifications
                # - SMS notifications

        except Exception as e:
            logger.error(
                f"Error creating notification for message {instance.message_id}: {str(e)}")


@receiver(post_save, sender=Notification)
def send_real_time_notification(sender, instance, created, **kwargs):
    """
    Signal to handle real-time notification delivery when a notification is created.
    This can be extended to integrate with WebSockets, email, push notifications, etc.
    """
    if created:
        try:
            # Placeholder for real-time notification delivery
            # In a real implementation, you might:
            # 1. Send WebSocket message
            # 2. Send push notification
            # 3. Send email
            # 4. Send SMS

            logger.info(
                f"Real-time notification ready for delivery: {instance.title} to {instance.user.email}")

            # Example: Send email notification (you would implement this)
            # send_email_notification(instance)

            # Example: Send push notification (you would implement this)
            # send_push_notification(instance)

        except Exception as e:
            logger.error(
                f"Error delivering notification {instance.notification_id}: {str(e)}")


@receiver(pre_save, sender=Message)
def update_conversation_timestamp(sender, instance, **kwargs):
    """
    Optional: Update conversation timestamp when new message is added
    """
    try:
        if instance.conversation_id:
            # You could add a last_activity field to Conversation model
            # and update it here
            pass
    except Exception as e:
        logger.error(f"Error updating conversation timestamp: {str(e)}")


def send_email_notification(notification):
    """
    Helper function to send email notifications
    """
    # Implementation for email notifications
    # You would integrate with your email service here
    pass


def send_push_notification(notification):
    """
    Helper function to send push notifications
    """
    # Implementation for push notifications
    # You would integrate with your push notification service here
    pass
