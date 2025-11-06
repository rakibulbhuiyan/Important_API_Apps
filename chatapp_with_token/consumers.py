import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db.models import Q
import jwt

from project import settings
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_room_id = self.scope['url_route']['kwargs']['room_name']  
        self.room_group_name = f'chat_{self.chat_room_id}'

        query_string = self.scope.get('query_string', b'').decode()
        query_params = {}
        
        if query_string:
            for param in query_string.split('&'):
                if '=' in param:
                    key, value = param.split('=', 1)
                    query_params[key] = value
    
        self.token = query_params.get('token')
        print(f"Token received: {self.token}")
        
        if not self.token:
            print("No token provided")
            await self.close()
            return

        self.user = await self.get_user_from_token(self.token)
        print(f"User connecting: {self.user}")

        if not self.user or self.user.is_anonymous:
            print("Authentication failed")
            await self.close()
        else:
            if await self.is_participant():
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()
                await self.mark_messages_as_read()
                print(f"User {self.user} connected to chat room {self.chat_room_id}")
            else:
                print("User is not a participant")
                await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            text_data_json = json.loads(text_data)
            message_content = text_data_json.get('message')
            message_type = text_data_json.get('type', 'chat_message')

            if message_type == 'chat_message' and message_content:
                saved_message = await self.save_message(message_content)
                
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message_id': str(saved_message.id),
                        'message': saved_message.message,
                        'sender_id': self.user.id,
                        'sender_email': self.user.email,
                        'timestamp': saved_message.created_at.isoformat(),
                        'read': saved_message.read,
                    }
                )
            elif message_type == 'read_receipt':
                await self.mark_messages_as_read()
                await self.send(text_data=json.dumps({
                    'status': 'success',
                    'status_code': 200,
                    'message': 'Messages marked as read',
                    'data': {}
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'status': 'error',
                'status_code': 400,
                'message': 'Invalid JSON',
                'data': {}
            }))

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'status': 'success',
            'status_code': 200,
            'message': 'New message received',
            'data': {
                'message_id': event['message_id'],
                'message': event['message'],
                'sender_id': event['sender_id'],
                'sender_email': event['sender_email'],
                'timestamp': event['timestamp'],
                'read': event['read'],
            }
        }))

    @database_sync_to_async
    def save_message(self, message_content):
        chat_room = ChatRoom.objects.get(id=self.chat_room_id)
        receiver = chat_room.repair_shop if self.user == chat_room.car_owner else chat_room.car_owner

        message = Message.objects.create(
            chat_room=chat_room,
            sender=self.user,
            receiver=receiver,  
            message=message_content
        )
        return message

    @database_sync_to_async
    def is_participant(self):
        return ChatRoom.objects.filter(
            id=self.chat_room_id
        ).filter(
            Q(car_owner=self.user) | Q(repair_shop=self.user)
        ).exists()

    @database_sync_to_async
    def mark_messages_as_read(self):
        Message.objects.filter(
            chat_room_id=self.chat_room_id,
            read=False
        ).exclude(sender=self.user).update(read=True)

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            user = User.objects.get(id=payload['user_id'])
            return user
        except (jwt.DecodeException, jwt.ExpiredSignatureError, User.DoesNotExist):
            return None