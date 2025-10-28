from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification

# optional kinds to respect preferences
K_NEW_BOOKING = "new_booking"
K_APPT_REMINDER = "appointment_reminder"
K_CLIENT_MESSAGE = "client_message"

def _professional_allows(professional, kind: str | None) -> bool:
    if kind is None:
        return True
    pref = getattr(professional, "notification_preferences", None)
    if not pref:
        return True  # default allow
    return {
        K_NEW_BOOKING: pref.new_booking_notifications,
        K_APPT_REMINDER: pref.appointment_reminders,
        K_CLIENT_MESSAGE: pref.client_messages,
    }.get(kind, True)

def create_notification(receiver, title, message, user_type, meta=None, kind: str | None = None):
    """
    receiver: User OR Professional instance
    user_type: 'customer' | 'professional'
    kind: one of K_* (applies only when receiver is Professional)
    """
    if hasattr(receiver, "user"):  # Professional
        if not _professional_allows(receiver, kind):
            return None
        notif = Notification.objects.create(
            receiver_professional=receiver,
            title=title, message=message, user_type=user_type, meta=meta or {}
        )
        group_user_id = receiver.user.id
    else:  # User
        notif = Notification.objects.create(
            receiver_user=receiver,
            title=title, message=message, user_type=user_type, meta=meta or {}
        )
        group_user_id = receiver.id

    async_to_sync(get_channel_layer().group_send)(
        f"user_{group_user_id}",
        {"type": "send_notification",
         "data": {
             "id": notif.id,
             "title": notif.title,
             "message": notif.message,
             "user_type": notif.user_type,
             "is_read": notif.is_read,
             "meta": notif.meta or {},
             "created_at": notif.created_at.isoformat(),
         }}
    )
    return notif
