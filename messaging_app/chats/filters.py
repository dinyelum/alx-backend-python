# chats/filters.py
import django_filters
from django_filters import rest_framework as filters
from .models import Message, Conversation
from django.utils import timezone
from datetime import timedelta


class MessageFilter(filters.FilterSet):
    """
    Filter class for messages to retrieve conversations with specific users or messages within a time range
    """
    # Filter by specific user (participant in conversation)
    participant = filters.UUIDFilter(
        field_name='conversation__participants__user_id', lookup_expr='exact')

    # Filter by sender
    sender = filters.UUIDFilter(
        field_name='sender__user_id', lookup_expr='exact')

    # Filter by time range
    start_date = filters.DateTimeFilter(
        field_name='sent_at', lookup_expr='gte')
    end_date = filters.DateTimeFilter(field_name='sent_at', lookup_expr='lte')

    # Filter by today, last_week, last_month
    time_range = filters.ChoiceFilter(
        choices=[
            ('today', 'Today'),
            ('last_week', 'Last Week'),
            ('last_month', 'Last Month'),
            ('last_year', 'Last Year')
        ],
        method='filter_by_time_range'
    )

    # Search filter for message content
    search = filters.CharFilter(
        field_name='message_body', lookup_expr='icontains')

    class Meta:
        model = Message
        fields = ['conversation', 'sender', 'sent_at']

    def filter_by_time_range(self, queryset, name, value):
        """
        Custom method to filter by time ranges
        """
        now = timezone.now()

        if value == 'today':
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return queryset.filter(sent_at__gte=start_date)

        elif value == 'last_week':
            start_date = now - timedelta(days=7)
            return queryset.filter(sent_at__gte=start_date)

        elif value == 'last_month':
            start_date = now - timedelta(days=30)
            return queryset.filter(sent_at__gte=start_date)

        elif value == 'last_year':
            start_date = now - timedelta(days=365)
            return queryset.filter(sent_at__gte=start_date)

        return queryset


class ConversationFilter(filters.FilterSet):
    """
    Filter class for conversations
    """
    participant = filters.UUIDFilter(
        field_name='participants__user_id', lookup_expr='exact')

    # Filter by number of participants
    min_participants = filters.NumberFilter(
        field_name='participants__count', lookup_expr='gte')
    max_participants = filters.NumberFilter(
        field_name='participants__count', lookup_expr='lte')

    # Filter by creation date
    created_after = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='gte')
    created_before = filters.DateTimeFilter(
        field_name='created_at', lookup_expr='lte')

    class Meta:
        model = Conversation
        fields = ['participants']

    def filter_queryset(self, queryset):
        """
        Annotate with participant count for filtering
        """
        queryset = queryset.annotate(
            participants_count=models.Count('participants'))
        return super().filter_queryset(queryset)
