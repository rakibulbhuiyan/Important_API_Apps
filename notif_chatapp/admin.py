from django.contrib import admin
from .models import Notification, NotificationPreference

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user_type", "is_read", "created_at")
    list_filter = ("user_type", "is_read", "created_at")
    search_fields = ("title", "message")

@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ("professional", "new_booking_notifications", "appointment_reminders", "client_messages", "updated_at")
    list_filter = ("new_booking_notifications", "appointment_reminders", "client_messages")
    search_fields = ("professional__user__email",)
