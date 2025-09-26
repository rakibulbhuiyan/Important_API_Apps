from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils import timezone
import uuid

User = get_user_model()

class ZoomMeeting(models.Model):
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('started', 'Started'), 
        ('ended', 'Ended'),
        ('cancelled', 'Cancelled')
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    zoom_meeting_id = models.CharField(max_length=20, unique=True)
    
    # Users
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hosted_meetings')
    participant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, 
                                  related_name='participated_meetings', null=True, blank=True)
    participant_email = models.EmailField(blank=True, null=True)
    
    # Meeting info
    topic = models.CharField(max_length=200)
    agenda = models.TextField(blank=True, null=True)
    scheduled_time = models.DateTimeField()
    duration = models.IntegerField(default=60)  # minutes
    
    # Zoom URLs
    join_url = models.URLField()
    start_url = models.URLField()
    password = models.CharField(max_length=10, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-scheduled_time']
    
    def __str__(self):
        return f"{self.topic} - {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}"
    


# from django.db import models

# class MeetingLog(models.Model):
#     meeting_id = models.CharField(max_length=255)
#     event_type = models.CharField(max_length=100)
#     participant_email = models.EmailField(null=True, blank=True)
#     timestamp = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"{self.event_type} - {self.meeting_id}"