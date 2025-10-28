import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_authenticated:
            await self.channel_layer.group_add(f"user_{self.user.id}", self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(f"user_{self.user.id}", self.channel_name)

    async def receive(self, text_data):
        pass

    async def send_notification(self, event):
        notification = event["notification"]
        await self.send(text_data=json.dumps({
            "message": notification,
        }))