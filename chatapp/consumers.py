# ...existing code...
from concurrent.futures import ThreadPoolExecutor
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)

User = get_user_model()
from django.utils import timezone
from django.core.cache import cache

PRESENCE_TTL = 120
MAX_MESSAGE_LENGTH = 2000
HISTORY_LIMIT = 50

class ChatConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.executor = ThreadPoolExecutor(max_workers=1)

        
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = await self._get_user(self.user_id)
        print("this is user",self.user)
        if self.user is AnonymousUser:
            await self.close()
        self.room_group_name = f'chat_{self.room_id}'
        # self.user = self.scope.get('user')
        await self.channel_layer.group_add(
                self.room_group_name,   
                self.channel_name
            )
        
        # check presence before connnect
        cache.set(f"user:{self.user.id}:online", 1, timeout=PRESENCE_TTL)
        cache.set(f"user:{self.user.id}:last_seen", timezone.now().isoformat(), timeout=None)
        await self.accept()

 
    async def disconnect(self, close_code):
        # 🔹 Presence: soft offline — only last_seen  updated
        try:
            cache.set(f"user:{self.user.id}:last_seen", timezone.now().isoformat(), timeout=None)
        except Exception:
            pass
        # Leave room group
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception:
            logger.exception("Error discarding group for room %s")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'message': 'invalid_json'}))
            return
        
        # 🔹 Presence heartbeat (WS)
        if isinstance(data, dict) and data.get("type") == "ping":
            cache.set(f"user:{self.user.id}:online", 1, timeout=PRESENCE_TTL)
            cache.set(f"user:{self.user.id}:last_seen", timezone.now().isoformat(), timeout=None)
            return

        message_type = data.get('type', 'chat_message')

        if message_type == 'chat_message':
            message_content = (data.get('message') or '').strip()
            if not message_content:
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'empty_message'}))
                return
           
            try:
                message = await self.save_message(message_content)
            except Exception:
                logger.exception("Failed to save message in room %s", self.room_id)
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'save_failed'}))
                return

            # Broadcast to group
            await self.channel_layer.group_send(
                self.room_group_name,
                {   
                    'type': 'chat_message',
                    'message': message_content,
                    'user_role': self.user.role,
                    'message_id': message.id,
                    'is_read': message.is_read,
                    'created_at': message.created_at.isoformat()
                }   
            )

        elif message_type == 'mark_read':
            message_ids = data.get('message_ids', [])
            if not isinstance(message_ids, list):
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'invalid_message_ids'}))
                return
            try:
                updated = await self.mark_messages_read(message_ids)
                await self.send(text_data=json.dumps({'type': 'mark_read_ack', 'message_ids': message_ids, 'updated': updated}))
            except Exception:
                logger.exception("Failed to mark messages read in room %s", self.room_id)
                await self.send(text_data=json.dumps({'type': 'error', 'message': 'mark_read_failed'}))

    async def chat_message(self, event):
        # Send message to WebSocket
        try:
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': event['message'],
                'user_role': event['user_role'],
                'message_id': event['message_id'],
                'is_read': event['is_read'],
                'created_at': event['created_at']
            }))
        except Exception:
            logger.exception("Failed to send chat_message to websocket for room %s", self.room_id)

    @database_sync_to_async
    def verify_room_membership(self):
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            # Adjust to your model: support participants M2M or explicit customer/professional fields
            if hasattr(room, 'participants'):
                return room.participants.filter(id=self.user.id).exists()
            return self.user == getattr(room, 'customer', None) or self.user == getattr(room, 'professional', None)
        except ObjectDoesNotExist:
            return False
        except Exception:
            logger.exception("Exception in verify_room_membership for room %s", self.room_id)
            raise

    @database_sync_to_async
    def save_message(self, content):
        try:
            room = ChatRoom.objects.get(id=self.room_id)

            message = Message.objects.create(
                room=room,
                sender=self.user,
                content=content
            )
            return message
        except Exception:
            logger.exception("Exception saving message for room %s and user %s", self.room_id, getattr(self.user, "id", None))
            raise

    @database_sync_to_async
    def get_room_messages(self, limit=None):
        try:
            if limit is None:
                limit = HISTORY_LIMIT
            qs = Message.objects.filter(room_id=self.room_id).select_related('sender').order_by('-created_at')[:limit]
            messages = list(reversed(qs))  # chronological order
            return [{
                'id': msg.id,
                'content': msg.content,
                'sender_id': getattr(msg.sender, 'id', None),
                'sender_email': getattr(msg.sender, 'email', None),
                'sender_role': getattr(msg.sender, 'role', None),
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat()
            } for msg in messages]
        except Exception:
            logger.exception("Exception fetching messages for room %s", self.room_id)
            raise

    @database_sync_to_async
    def mark_messages_read(self, message_ids):
        try:
            updated = Message.objects.filter(
                id__in=message_ids,
                room_id=self.room_id
            ).exclude(sender=self.user).update(is_read=True)
            return updated
        except Exception:
            logger.exception("Exception marking messages read in room %s", self.room_id)
            raise

    @database_sync_to_async
    def _get_user(self, user_id):
        return User.objects.get(id=user_id)
# ...existing code...