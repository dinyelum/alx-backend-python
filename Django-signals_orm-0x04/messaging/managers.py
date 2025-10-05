# messaging/managers.py
from django.db import models
from django.db.models import Q


class UnreadMessagesManager(models.Manager):
    """
    Custom manager to filter unread messages for a specific user
    """

    def unread_for_user(self, user):
        """
        Return all unread messages for a specific user
        Optimized with .only() to retrieve only necessary fields
        """
        return self.filter(
            Q(receiver=user) | Q(conversation__participants=user),
            is_read=False
        ).exclude(
            sender=user  # Exclude messages sent by the user
        ).select_related(
            'sender', 'conversation'
        ).only(
            'message_id',
            'content',
            'timestamp',
            'sender__user_id',
            'sender__first_name',
            'sender__last_name',
            'sender__email',
            'conversation__conversation_id'
        ).distinct()

    def mark_as_read(self, user, message_ids=None):
        """
        Mark messages as read for a user
        If message_ids is provided, mark only those messages
        Otherwise, mark all unread messages for the user
        """
        queryset = self.unread_for_user(user)

        if message_ids:
            queryset = queryset.filter(message_id__in=message_ids)

        updated_count = queryset.update(is_read=True)
        return updated_count

    def unread_count_for_user(self, user):
        """
        Get the count of unread messages for a user
        """
        return self.unread_for_user(user).count()


class ThreadedMessageManager(models.Manager):
    """
    Custom manager for threaded messages with optimized queries
    """

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
            queryset=self.model.objects.select_related('sender', 'receiver').prefetch_related(
                Prefetch('replies', queryset=self.model.objects.select_related(
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
                queryset=self.model.objects.select_related('sender', 'receiver').prefetch_related(
                    get_replies_prefetch()
                )
            )

        return self.select_related(
            'sender', 'receiver', 'parent_message', 'parent_message__sender'
        ).prefetch_related(
            get_replies_prefetch()
        ).get(message_id=message_id)
