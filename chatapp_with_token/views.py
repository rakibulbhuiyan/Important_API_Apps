from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.user.models import RepairShopProfile
from .models import ChatRoom, Message
from .serializers import (
    ChatRoomSerializer,
    MessageSerializer,
    CreateChatRoomSerializer,
    UserSerializer,
    MessageBoxSerializer
)
from django.contrib.auth import get_user_model

User = get_user_model()

class ChatRoomViewSet(viewsets.ModelViewSet):
    queryset = ChatRoom.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateChatRoomSerializer
        return ChatRoomSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response({
            'status': 'success',
            'status_code': status.HTTP_201_CREATED,
            'message': 'Chatroom created successfully',
            'room_id': serializer.data['id'],
            'data': serializer.data
        }, status=status.HTTP_201_CREATED, headers=headers)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'status': 'success',
                'status_code': status.HTTP_200_OK,
                'message': 'Chatrooms retrieved successfully',
                'data': serializer.data
            })
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'status': 'success',
            'status_code': status.HTTP_200_OK,
            'message': 'Chatrooms retrieved successfully',
            'data': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'status': 'success',
            'status_code': status.HTTP_200_OK,
            'message': 'Chatroom retrieved successfully',
            'data': serializer.data
        })

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({
            'status': 'success',
            'status_code': status.HTTP_200_OK,
            'message': 'Chatroom updated successfully',
            'data': serializer.data
        })

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({
            'status': 'success',
            'status_code': status.HTTP_204_NO_CONTENT,
            'message': 'Chatroom deleted successfully',
            'data': {}
        }, status=status.HTTP_204_NO_CONTENT)

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        chat_room_id = self.kwargs['chatroom_id']

        chat_room = ChatRoom.objects.filter(
            id=chat_room_id
        ).filter(
            Q(car_owner=self.request.user) | Q(repair_shop=self.request.user)
        ).first()

        if not chat_room:
            raise PermissionDenied("You don't have access to this chat room")

        queryset = Message.objects.filter(
            chat_room=chat_room
        ).select_related('sender', 'chat_room').order_by('-created_at')

        unread_messages = queryset.filter(receiver=self.request.user, read=False)
        unread_messages.update(read=True)

        return queryset

    def perform_create(self, serializer):
        chat_room_id = self.kwargs['chatroom_id']

        chat_room = get_object_or_404(
            ChatRoom,
            Q(id=chat_room_id) &
            (Q(car_owner=self.request.user) | Q(repair_shop=self.request.user))
        )

        receiver = chat_room.repair_shop if self.request.user == chat_room.car_owner else chat_room.car_owner
        serializer.save(chat_room=chat_room, sender=self.request.user, receiver=receiver, read=False)

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class UnreadMessagesCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = Message.objects.filter(receiver=request.user, read=False).count()
        return Response({
            'status': 'success',
            'status_code': status.HTTP_200_OK,
            'message': 'Unread messages count retrieved successfully',
            'unread_count': count})
    

class SearchRepairShopsView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if not query:
            return User.objects.none()
        
        profile_qs = RepairShopProfile.objects.filter(
            Q(shop_name__icontains=query) |
            Q(user__name__icontains=query) |
            Q(user__email__icontains=query) |
            Q(rating__icontains=query) |
            Q(distance__icontains=query) |
            Q(open_today=True)
        ).values_list('user_id', flat=True)

        user_ids = list(profile_qs)
        if not user_ids:
            return User.objects.none()

        return (
            User.objects
            .filter(id__in=user_ids)
            .select_related('car_owner')
            .prefetch_related('repair_shop')
            .order_by('name')
        )


class MessageBoxView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        chat_rooms = ChatRoom.objects.filter(
            Q(car_owner=user) | Q(repair_shop=user)
        ).prefetch_related('messages', 'car_owner', 'repair_shop')

        serializer = MessageBoxSerializer(chat_rooms, many=True, context={'request': request})
        return Response({
            'status': 'success',
            'status_code': status.HTTP_200_OK,
            'message': 'Message box retrieved successfully',
            'data': serializer.data
        })