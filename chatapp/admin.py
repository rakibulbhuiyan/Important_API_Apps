from django.contrib import admin
from .models import ChatRoom, Message

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'professional', 'message_count', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['customer__email', 'professional__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def message_count(self, obj):
        return obj.messages.count()
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'room_id', 'sender', 'content_preview', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at', 'sender__role']
    search_fields = ['sender__email', 'content', 'room__customer__email', 'room__professional__email']
    readonly_fields = ['created_at']
    raw_id_fields = ['room', 'sender']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
    
    def room_id(self, obj):
        return obj.room.id
    room_id.short_description = 'Room ID'