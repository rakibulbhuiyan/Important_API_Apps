from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'chatrooms', views.ChatRoomViewSet, basename='chatroom')

urlpatterns = [
    path('', include(router.urls)),
    path('chatrooms/<int:chatroom_id>/messages/', views.MessageViewSet.as_view({'get': 'list', 'post': 'create'}), name='message-list'),
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('unread-count/', views.UnreadMessagesCountView.as_view(), name='unread-count'),
    path('search-repair-shops/', views.SearchRepairShopsView.as_view(), name='search-repair-shops'),

    path('message-box/', views.MessageBoxView.as_view(), name='message-box'),
]