# messaging/admin.py
from django.contrib import admin
from .models import User, Conversation, Message, Notification, MessageHistory


class MessageHistoryInline(admin.TabularInline):
    model = MessageHistory
    extra = 0
    readonly_fields = ['history_id', 'edited_at', 'version_number']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


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
                    'timestamp', 'is_read', 'edited', 'edited_at', 'content_preview']
    list_filter = ['timestamp', 'is_read', 'edited', 'edited_at']
    readonly_fields = ['message_id', 'timestamp', 'edited', 'edited_at']
    search_fields = ['content', 'sender__email']
    inlines = [MessageHistoryInline]

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'


@admin.register(MessageHistory)
class MessageHistoryAdmin(admin.ModelAdmin):
    list_display = ['history_id', 'message', 'version_number',
                    'edited_by', 'edited_at', 'content_preview']
    list_filter = ['edited_at', 'version_number']
    readonly_fields = ['history_id', 'edited_at']
    search_fields = ['old_content', 'new_content', 'message__message_id']

    def content_preview(self, obj):
        old_preview = obj.old_content[:30] + \
            '...' if len(obj.old_content) > 30 else obj.old_content
        new_preview = obj.new_content[:30] + \
            '...' if len(obj.new_content) > 30 else obj.new_content
        return f"'{old_preview}' → '{new_preview}'"
    content_preview.short_description = 'Edit Preview'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'user',
                    'notification_type', 'title', 'is_read', 'timestamp']
    list_filter = ['notification_type', 'is_read', 'timestamp']
    readonly_fields = ['notification_id', 'timestamp']
    search_fields = ['user__email', 'title', 'content']
    actions = ['mark_as_read']

    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark selected notifications as read"
