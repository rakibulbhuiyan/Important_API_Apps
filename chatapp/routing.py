from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # re_path(r'ws/chat/<int:id>/', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<user_id>\w+)/(?P<room_id>\w+)/$', consumers.ChatConsumer.as_asgi()),
]