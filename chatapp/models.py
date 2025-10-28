from django.db import models
from django.conf import settings

class ChatRoom(models.Model):
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,null=True,
        related_name='customer_rooms',
        limit_choices_to={'role': 'customer'}
    )
    professional = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,null=True,
        related_name='professional_rooms',
        limit_choices_to={'role': 'professional'}
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['customer', 'professional']
        ordering = ['-updated_at']

    def __str__(self):
        return f"Chat: {self.customer.email} - {self.professional.email}"


class Message(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.SET_NULL,null=True, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.sender.email}: {self.content[:50]}"
