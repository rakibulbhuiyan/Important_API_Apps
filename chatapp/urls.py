from django.urls import path
from .views import (
    ChatRoomListCreateAPIView,
    ChatRoomDetailAPIView,
    ChatRoomMessagesAPIView,
    ChatRoomMarkReadAPIView,
    UnreadSummaryAPIView,
    MessageListCreateAPIView,
    MessageMarkReadAPIView,
    MessageMarkMultipleReadAPIView,
    MessageUnreadCountAPIView
)

urlpatterns = [
    # ChatRoom endpoints
    path('rooms/', ChatRoomListCreateAPIView.as_view(), name='chatroom-list-create'),
    path('rooms/<int:room_id>/', ChatRoomDetailAPIView.as_view(), name='chatroom-detail'),
    path('rooms/<int:room_id>/messages/', ChatRoomMessagesAPIView.as_view(), name='chatroom-messages'),
    path('rooms/<int:room_id>/mark_read/', ChatRoomMarkReadAPIView.as_view(), name='chatroom-mark-read'),
    path('rooms/unread_summary/', UnreadSummaryAPIView.as_view(), name='chatroom-unread-summary'),

    # Message endpoints
    path('messages/', MessageListCreateAPIView.as_view(), name='message-list-create'),
    path('messages/<int:message_id>/mark_read/', MessageMarkReadAPIView.as_view(), name='message-mark-read'),
    path('messages/mark_multiple_read/', MessageMarkMultipleReadAPIView.as_view(), name='message-mark-multiple-read'),
    path('messages/unread_count/', MessageUnreadCountAPIView.as_view(), name='message-unread-count'),
]


# Available URLs:
# 
# Chat Rooms:
# - GET    /api/rooms/                      - List all rooms
# - POST   /api/rooms/                      - Create new room
# - GET    /api/rooms/{id}/                 - Get specific room
# - GET    /api/rooms/{id}/messages/        - Get room messages
# - POST   /api/rooms/{id}/mark_read/       - Mark room messages as read
# - GET    /api/rooms/unread_summary/       - Get unread summary
# - POST   /api/rooms/start/           - Start with user
#
# Messages:
# - GET    /api/messages/                   - List all messages
# - POST   /api/messages/                   - Send new message
# - GET    /api/messages/{id}/              - Get specific message
# - PATCH  /api/messages/{id}/mark_read/    - Mark message as read
# - GET    /api/messages/unread_count/      - Get total unread count
# - POST   /api/messages/mark_multiple_read/ - Mark multiple as read
