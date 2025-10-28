from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db.models import Q, Max, Prefetch
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model

from .models import ChatRoom, Message
from .serializers import (
    ChatRoomSerializer,
    MessageSerializer,
    MessageCreateSerializer
)

User =get_user_model()
class ChatRoomListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """List all chat rooms for the current user"""
        user = request.user
        rooms = ChatRoom.objects.filter(
            Q(customer=user) | Q(professional=user)
        ).select_related('customer', 'professional'
        ).prefetch_related(
            Prefetch('messages', queryset=Message.objects.order_by('-created_at'))
        ).annotate(
            last_message_time=Max('messages__created_at')
        ).order_by('-last_message_time')

        serializer = ChatRoomSerializer(rooms, many=True, context={'request': request})
        return Response({
                "status": "success",
                "status_code": status.HTTP_200_OK,
                "message": "fetch your data successfully",
                "data": serializer.data
            })

    def post(self, request):
        current_user = request.user
        target_user_id = request.data.get("target_user_id")

        if not target_user_id:
            return Response({
                "status": "error",
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "target_user_id is required"
            })

        target_user = get_object_or_404(User, id=target_user_id)

        customer = None
        professional = None

        if current_user.role == "customer" and target_user.role == "professional":
            customer = current_user
            professional = target_user
        elif current_user.role == "professional" and target_user.role == "customer":
            customer = target_user
            professional = current_user
        else:
            return Response({
                "status": "created",
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Invalid user roles for chat creation"
            })

        existing_room = ChatRoom.objects.filter(
            professional=professional, customer=customer
        ).first()

        if existing_room:
            serializer = ChatRoomSerializer(existing_room, context={'request': request})
            return Response({
                "status": "success",
                "status_code": status.HTTP_200_OK,
                "message": "Chat Room already exists",
                "data": serializer.data
            })

        room = ChatRoom.objects.create(
            professional=professional,
            customer=customer
        )
        serializer = ChatRoomSerializer(room,context={'request': request})

        return Response({
            "status": "success",
            "status_code": status.HTTP_201_CREATED,
            "message": "Chat Room created successfully",
            "data": serializer.data
        })


class ChatRoomDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_id):
        """Retrieve a specific chat room"""
        room = get_object_or_404(ChatRoom, id=room_id)
        if request.user not in [room.customer, room.professional]:
            return Response({'error': 'You are not a member of this chat'}, status=403)

        serializer = ChatRoomSerializer(room, context={'request': request})
        return Response(serializer.data)


class ChatRoomMessagesAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, room_id):
        """Get messages of a chat room"""
        room = get_object_or_404(ChatRoom, id=room_id)
        if request.user not in [room.customer, room.professional]:
            return Response({'error': 'Access denied'}, status=403)

        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        messages = room.messages.select_related('sender').order_by('-created_at')[offset:offset+limit]
        messages = list(reversed(messages))

        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response({'count': room.messages.count(), 'results': serializer.data})


class ChatRoomMarkReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, room_id):
        """Mark all unread messages in this room as read"""
        room = get_object_or_404(ChatRoom, id=room_id)
        updated_count = Message.objects.filter(room=room, is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response({'status': 'success', 'marked_read': updated_count})


class UnreadSummaryAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get unread message count for each room"""
        user = request.user
        rooms = ChatRoom.objects.filter(Q(customer=user) | Q(professional=user))
        summary = []

        for room in rooms:
            unread = room.messages.filter(is_read=False).exclude(sender=user).count()
            if unread > 0:
                summary.append({
                    'room_id': room.id,
                    'unread_count': unread,
                    'other_user': room.professional.email if room.customer == user else room.customer.email
                })

        return Response({
            'total_unread': sum(item['unread_count'] for item in summary),
            'rooms': summary
        })


class MessageListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """List all messages for the user"""
        user = request.user
        messages = Message.objects.filter(
            Q(room__customer=user) | Q(room__professional=user)
        ).select_related('sender', 'room').order_by('-created_at')

        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        """Send a new message"""
        serializer = MessageCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(sender=request.user)
        message.room.save(update_fields=['updated_at'])
        output = MessageSerializer(message, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class MessageMarkReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, message_id):
        """Mark a specific message as read"""
        message = get_object_or_404(Message, id=message_id)
        if message.sender == request.user:
            return Response({'error': 'Cannot mark your own message as read'}, status=400)
        message.is_read = True
        message.save(update_fields=['is_read'])
        serializer = MessageSerializer(message, context={'request': request})
        return Response(serializer.data)


class MessageMarkMultipleReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Mark multiple messages as read"""
        message_ids = request.data.get('message_ids', [])
        if not message_ids:
            return Response({'error': 'message_ids is required'}, status=400)

        updated = Message.objects.filter(
            id__in=message_ids,
            room__in=ChatRoom.objects.filter(Q(customer=request.user) | Q(professional=request.user))
        ).exclude(sender=request.user).update(is_read=True)

        return Response({'status': 'success', 'marked_read': updated})


class MessageUnreadCountAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get total unread count"""
        count = Message.objects.filter(
            Q(room__customer=request.user) | Q(room__professional=request.user),
            is_read=False
        ).exclude(sender=request.user).count()
        return Response({'unread_count': count})
