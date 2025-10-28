# apps/bookings/tasks.py

from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from celery import shared_task

from apps.browse.models import Booking
from apps.notif_chatapp.utils import create_notification, K_APPT_REMINDER
from apps.notif_chatapp.models import Notification   # only for dedupe check


@shared_task
def send_appointment_reminders():
    """
    Send appointment reminders ~1 hour before start.
    Works even if the 1h window crosses midnight.
    Respects professional preferences via kind=K_APPT_REMINDER.
    """

    # Use local time if your business logic is local-time based. If you want pure UTC, use timezone.now()
    now = timezone.localtime()
    one_hour_later = now + timedelta(hours=1)

    # --- Time window over (booking_date + start_time) ---
    # A) Same-day window
    case_a = Q(
        booking_date=now.date(),
        start_time__gte=now.time(),
        start_time__lte=one_hour_later.time()
    )

    # B) Cross-midnight window (e.g., 23:45 → 00:30 next day)
    case_b = Q()
    if one_hour_later.date() != now.date():
        case_b = Q(
            booking_date=one_hour_later.date(),
            start_time__lte=one_hour_later.time()
        )

    # Fetch upcoming confirmed bookings in the next ~1 hour
    bookings = (
        Booking.objects
        .filter((case_a | case_b), status="confirmed")
        .select_related("professional__user", "user")   # fewer queries
        .only(  # optional micro-optimization
            "id", "booking_date", "start_time",
            "professional_id", "user_id",
            "status",
            "professional__user__first_name", "professional__user__last_name", "professional__user__email",
            "user__first_name", "user__last_name", "user__email",
        )
    )

    for booking in bookings:
        professional = booking.professional          # Professional instance
        customer = booking.user                      # User instance

        # Human-readable time
        start_txt = booking.start_time.strftime("%I:%M %p")

        # ---- De-dupe so the same reminder isn't sent repeatedly ----
        pro_already = Notification.objects.filter(
            receiver_professional=professional,
            user_type="professional",
            meta__booking_id=booking.id,
            title="Upcoming Appointment Reminder",
        ).exists()

        cust_already = Notification.objects.filter(
            receiver_user=customer,
            user_type="customer",
            meta__booking_id=booking.id,
            title="Appointment Reminder",
        ).exists()

        # ---- Professional reminder (preference-aware) ----
        if not pro_already:
            create_notification(
                receiver=professional,                     # unified param
                title="Upcoming Appointment Reminder",
                message=f"You have an appointment with {customer.first_name or customer.email} at {start_txt}.",
                user_type="professional",
                meta={"booking_id": booking.id},
                kind=K_APPT_REMINDER,                      # respects professional.appointment_reminders
            )

        # ---- Customer reminder (always send; pref is for professionals only here) ----
        if not cust_already:
            pro_user = getattr(professional, "user", None)
            pro_name = (getattr(pro_user, "get_full_name", lambda: "")() or
                        getattr(pro_user, "email", "the professional"))

            create_notification(
                receiver=customer,
                title="Appointment Reminder",
                message=f"You have an appointment with {pro_name} at {start_txt}.",
                user_type="customer",
                meta={"booking_id": booking.id},
                kind=None,
            )
