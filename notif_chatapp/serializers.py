from rest_framework import serializers
from .models import *
from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification

User = get_user_model()



class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "receiver_user",
            "receiver_professional",
            "title",
            "message",
            "user_type",
            "meta",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields


class UserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email")  # or add first_name/last_name if available 


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "new_booking_notifications",
            "appointment_reminders",
            "client_messages",
        ]



