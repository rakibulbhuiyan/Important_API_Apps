from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()


class ChatRoom(models.Model):
    car_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_rooms_as_owner',
        null=True,  
        blank=True,
    )
    repair_shop = models.ForeignKey(User, on_delete=models.CASCADE, related_name='repair_shop_ChatRoom')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.car_owner.email}'s ChatRoom with {self.repair_shop.email}"
    

class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    message = models.TextField(null=True, blank=True)
    metadata = models.JSONField(null=True, blank=True)  
    is_delivered = models.BooleanField(default=False)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.sender.email}'s message to {self.receiver.email}"
    
    class Meta:
        ordering = ['-created_at']




