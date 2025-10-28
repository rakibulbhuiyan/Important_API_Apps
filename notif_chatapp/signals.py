from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.browse.models import Booking
from apps.browse.models import Review, ReviewReply
from .utils import create_notification, K_NEW_BOOKING, K_CLIENT_MESSAGE

@receiver(post_save, sender=Booking)
def booking_created(sender, instance, created, **kwargs):

    if not created: return
    
    create_notification(
        receiver=instance.professional,   # Professional instance
        title="New Booking",
        # message=f"{instance.customer.get_full_name() or instance.customer.email} booked you.",
        message=f"{instance.user or instance.user.email} booked you.",
        user_type="professional",
        meta={"booking_id": instance.id},
        kind=K_NEW_BOOKING,
    )

@receiver(post_save, sender=Review)
def review_created(sender, instance, created, **kwargs):
    if not created:
        return

    # Use `instance.provider` instead of `instance.professional`
    create_notification(
        receiver=instance.provider.user,  # Access the user associated with the provider
        title="New Review",
        message="You received a new review.",
        user_type="professional",
        meta={"review_id": instance.id},
        kind=K_CLIENT_MESSAGE,
    )

@receiver(post_save, sender=ReviewReply)
def reply_created(sender, instance, created, **kwargs):
    if not created: return
    create_notification(
        receiver=instance.review.user,  # customer(User)
        title="Reply to your review",
        message=f"{instance.review.professional.user.get_full_name()} replied.",
        user_type="customer",
        meta={"review_id": instance.review.id, "reply_id": instance.id},
        kind=None,
    )
