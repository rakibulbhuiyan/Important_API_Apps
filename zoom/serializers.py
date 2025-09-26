# Simple serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from .models import ZoomMeeting

User = get_user_model()

class ZoomMeetingSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source='host.get_full_name', read_only=True)
    
    class Meta:
        model = ZoomMeeting
        fields = [
            'id', 'zoom_meeting_id', 'topic', 'agenda', 
            'scheduled_time', 'duration', 'join_url', 'start_url', 
            'password', 'status', 'host', 'host_name',
            'participant', 'participant_email', 'created_at'
        ]
        read_only_fields = ['id', 'zoom_meeting_id', 'join_url', 'start_url', 'password']

class CreateMeetingSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=200, default='Professional Meeting')
    agenda = serializers.CharField(required=False, allow_blank=True)
    scheduled_time = serializers.DateTimeField(required=False)
    duration = serializers.IntegerField(default=60, min_value=15, max_value=480)
    participant_email = serializers.EmailField(required=False)
    
    def validate_scheduled_time(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError("Time must be in future")
        return value