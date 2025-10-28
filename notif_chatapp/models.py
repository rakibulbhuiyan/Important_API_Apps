from django.db import models
from django.conf import settings
from apps.browse.models import Proffessional

class Notification(models.Model):
    USER_TYPES = [
        ("customer", "Customer"),
        ("professional", "Professional"),
    ]

    # Either receiver_user OR receiver_professional will be set
    receiver_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True, blank=True
    )
    receiver_professional = models.ForeignKey(
        Proffessional,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True, blank=True
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    is_read = models.BooleanField(default=False)
    meta = models.JSONField(null=True, blank=True)  # optional extra data: {"booking_id":1, "review_id":2}
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_read"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        if self.receiver_user:
            return f"Notification for {self.receiver_user.email}: {self.title}"
        if self.receiver_professional:
            return f"Notification for {self.receiver_professional.user.email}: {self.title}"
        return f"Notification: {self.title}"



class Conversation(models.Model):
    """
    A conversation between two or more participants.
    For this project it's likely 1 user <-> 1 professional, but this supports N participants.
    """
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="conversations")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Conversation {self.pk} ({self.participants.count()} participants)"



class NotificationPreference(models.Model):
    professional = models.OneToOneField(
        Proffessional,
        on_delete=models.CASCADE,
        related_name="notification_preferences"
    )
    new_booking_notifications = models.BooleanField(default=True)
    appointment_reminders = models.BooleanField(default=True)
    client_messages = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification Preferences for {self.professional.user.email}"