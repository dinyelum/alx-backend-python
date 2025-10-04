from django.contrib import admin
from .models import User, Conversation, Message, Notification


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['user_id', 'created_at']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['conversation_id', 'created_at', 'participants_count']
    list_filter = ['created_at']
    readonly_fields = ['conversation_id', 'created_at']
    filter_horizontal = ['participants']

    def participants_count(self, obj):
        return obj.participants.count()
    participants_count.short_description = 'Participants'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['message_id', 'sender', 'conversation',
                    'sent_at', 'is_read', 'message_preview']
    list_filter = ['sent_at', 'is_read']
    readonly_fields = ['message_id', 'sent_at']
    search_fields = ['message_body', 'sender__email']

    def message_preview(self, obj):
        return obj.message_body[:50] + '...' if len(obj.message_body) > 50 else obj.message_body
    message_preview.short_description = 'Message Preview'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'user',
                    'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    readonly_fields = ['notification_id', 'created_at']
    search_fields = ['user__email', 'title', 'content']
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark selected notifications as read"
