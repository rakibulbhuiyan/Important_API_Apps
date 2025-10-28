from rest_framework import serializers
from .models import ChatRoom, Message
from django.contrib.auth import get_user_model

User = get_user_model()
from django.utils import timezone
from django.core.cache import cache


class UserBasicSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()

    is_online = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'role', 'name', 'profile_pic','is_online','last_seen']

    def get_name(self, obj):
        if hasattr(obj, 'profile'):
            return f"{obj.profile.first_name or ''} {obj.profile.last_name or ''}".strip()
        elif hasattr(obj, 'professional'):
            return f"{obj.professional.first_name or ''} {obj.professional.last_name or ''}".strip()
        return obj.email

    def get_profile_pic(self, obj):
        request = self.context.get('request')
        if not request:
            return None
        if hasattr(obj, 'profile') and obj.profile.profile_pic:
            return request.build_absolute_uri(obj.profile.profile_pic.url)
        elif hasattr(obj, 'professional') and obj.professional.profile_pic:
            return request.build_absolute_uri(obj.professional.profile_pic.url)
        return None
    
    def get_is_online(self, obj):
        return bool(cache.get(f"user:{obj.id}:online"))

    def get_last_seen(self, obj):
        return cache.get(f"user:{obj.id}:last_seen")


class MessageSerializer(serializers.ModelSerializer):
    sender_info = UserBasicSerializer(source='sender', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'room', 'sender', 'sender_info', 'content', 'is_read', 'created_at']
        read_only_fields = ['sender', 'created_at', 'is_read']


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['room', 'content']

    def validate_room(self, value):
        user = self.context['request'].user
        # Check if user is part of this room
        if value.customer != user and value.professional != user:
            raise serializers.ValidationError("You are not a member of this chat room")
        return value


class ChatRoomSerializer(serializers.ModelSerializer):
    customer_info = UserBasicSerializer(source='customer', read_only=True)
    professional_info = UserBasicSerializer(source='professional', read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = [
            'id', 'customer', 'professional', 
            'customer_info', 'professional_info',
            'last_message', 'unread_count', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'id': last_msg.id,
                'content': last_msg.content,
                'created_at': last_msg.created_at,
                'sender_id': last_msg.sender.id,
                'sender_email': last_msg.sender.email,
                'is_read': last_msg.is_read
            }
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0


