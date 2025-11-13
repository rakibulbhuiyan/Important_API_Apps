from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.http import JsonResponse
from django.contrib.auth import get_user_model

User = get_user_model()

class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    If the incoming social login's email already exists in our DB,
    stop the flow and return a JSON response informing the client.
    """
    def pre_social_login(self, request, sociallogin):
        # If sociallogin already linked to a user, nothing to do
        if sociallogin.is_existing:
            return

        # Try to get email from social account extra_data (provider dependent)
        email = None
        if sociallogin.account and sociallogin.account.extra_data:
            email = sociallogin.account.extra_data.get("email")

        # Fallback to sociallogin.user.email (sometimes populated)
        if not email:
            email = getattr(sociallogin.user, "email", None)

        # If no email, we can't check — let normal flow continue
        if not email:
            return

        # If a user with this email already exists, stop and return message
        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        # Return a JSON response and abort the allauth flow
        # Message exactly as you requested:
        payload = {"detail": "You already have an account in this email."}
        raise ImmediateHttpResponse(JsonResponse(payload, status=400))
