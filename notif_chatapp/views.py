from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Notification, NotificationPreference

def inbox_qs(user):
    return (Notification.objects.filter(receiver_professional=user.professional)
            if hasattr(user, "professional")
            else Notification.objects.filter(receiver_user=user))


class NotificationListAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = inbox_qs(request.user)
        is_read = request.query_params.get("is_read")
        if is_read in ("0","1"):
            qs = qs.filter(is_read=(is_read == "1"))

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        except ValueError:
            page, size = 1, 20

        total = qs.count()
        unread = inbox_qs(request.user).filter(is_read=False).count()
        start, end = (page-1)*size, (page-1)*size+size

        rows = list(qs.order_by("-created_at")
                      .values("id","title","message","user_type","is_read","meta","created_at")[start:end])

        for r in rows:
            r["meta"] = r["meta"] or {}
            r["created_at"] = r["created_at"].isoformat()

        return Response({"items": rows, "page": page, "page_size": size, "total": total, "unread": unread})

class NotificationMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request, pk):
        updated = inbox_qs(request.user).filter(id=pk, is_read=False).update(is_read=True)
        return Response({"updated": updated, "id": pk}, status=status.HTTP_200_OK)

class NotificationBulkMarkReadAPI(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        ids = request.data.get("ids", [])



class NotificationMarkAllReadAPI(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        updated = inbox_qs(request.user).filter(is_read=False).update(is_read=True)
        return Response({"updated": updated})

class NotificationUnreadCountAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        unread = inbox_qs(request.user).filter(is_read=False).count()
        return Response({"unread": unread})



# -----------------------notification preference-------------------

class NotificationPreferenceAPI(APIView):
    permission_classes = [IsAuthenticated]

    def _prof(self, user):
        return getattr(user, "professional", None)

    def get(self, request):
        prof = self._prof(request.user)
        if not prof:
            return Response({"detail":"Only professionals have preferences."}, status=403)
        pref, _ = NotificationPreference.objects.get_or_create(professional=prof)
        return Response({
            "new_booking_notifications": pref.new_booking_notifications,
            "appointment_reminders": pref.appointment_reminders,
            "client_messages": pref.client_messages,
        })

    def put(self, request):
        prof = self._prof(request.user)
        if not prof:
            return Response({"detail":"Only professionals have preferences."}, status=403)
        pref, _ = NotificationPreference.objects.get_or_create(professional=prof)
        data = request.data or {}
        if "new_booking_notifications" in data:
            pref.new_booking_notifications = bool(data["new_booking_notifications"])
        if "appointment_reminders" in data:
            pref.appointment_reminders = bool(data["appointment_reminders"])
        if "client_messages" in data:
            pref.client_messages = bool(data["client_messages"])
        pref.save(update_fields=["new_booking_notifications","appointment_reminders","client_messages","updated_at"])
        return Response({
            "new_booking_notifications": pref.new_booking_notifications,
            "appointment_reminders": pref.appointment_reminders,
            "client_messages": pref.client_messages,
        })




class TestNotificationAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        
        # Send notification to the user's group
        async_to_sync(channel_layer.group_send)(
            f"user_{request.user.id}",
            {
                "type": "send_notification",
                "notification": {
                    "title": "Test Notification",
                    "message": request.data.get("message", "This is a test notification!"),
                    "created_at": "2025-10-26T03:00:00Z"
                }
            }
        )
        
        return Response({"status": "notification sent"})
        if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
            return Response({"detail": "ids must be list[int]"}, status=400)
        updated = inbox_qs(request.user).filter(id__in=ids, is_read=False).update(is_read=True)
        return Response({"updated": updated, "ids": ids})