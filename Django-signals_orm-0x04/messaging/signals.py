# messaging/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.exceptions import ObjectDoesNotExist
from .models import Message, Notification, User, Conversation
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal to create notifications for the receiver when a new message is created.
    """
    if created:
        try:
            # Use the receiver field if specified, otherwise notify all other participants
            if instance.receiver:
                # Direct message to specific receiver
                receivers = [instance.receiver]
            else:
                # Group message - notify all participants except sender
                conversation = instance.conversation
                receivers = conversation.participants.exclude(
                    user_id=instance.sender.user_id)

            for receiver_user in receivers:
                # Create notification for each receiver
                notification = Notification.objects.create(
                    user=receiver_user,
                    message=instance,
                    notification_type='message',
                    title=f"New message from {instance.sender.first_name} {instance.sender.last_name}",
                    content=f"{instance.content[:100]}..." if len(
                        instance.content) > 100 else instance.content
                )

                logger.info(
                    f"Notification created for user {receiver_user.email}: {notification.title}")

        except Exception as e:
            logger.error(
                f"Error creating notification for message {instance.message_id}: {str(e)}")


@receiver(pre_save, sender=Message)
def set_receiver_if_not_provided(sender, instance, **kwargs):
    """
    Automatically set receiver for one-on-one conversations if not provided.
    """
    if not instance.receiver and instance.conversation:
        try:
            # For one-on-one conversations, set the other participant as receiver
            other_participants = instance.conversation.participants.exclude(
                user_id=instance.sender.user_id)
            if other_participants.count() == 1:
                instance.receiver = other_participants.first()
        except Exception as e:
            logger.error(f"Error setting receiver for message: {str(e)}")


@receiver(post_save, sender=Notification)
def send_real_time_notification(sender, instance, created, **kwargs):
    """
    Signal to handle real-time notification delivery when a notification is created.
    """
    if created:
        try:
            logger.info(
                f"Real-time notification ready for delivery: {instance.title} to {instance.user.email}")

            # Placeholder for real-time notification delivery methods:
            # - WebSocket notifications
            # - Email notifications
            # - Push notifications
            # - SMS notifications

        except Exception as e:
            logger.error(
                f"Error delivering notification {instance.notification_id}: {str(e)}")
