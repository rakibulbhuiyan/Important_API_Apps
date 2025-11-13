from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import (
    SignupSerializer, LoginSerializer, ProfileSerializer, RoleSelectionSerializer,
    PasswordResetRequestSerializer, PasswordResetChangeSerializer, ChangePasswordSerializer
)
from rest_framework import generics
User = get_user_model()

from django.db import transaction
from django.core.files.base import ContentFile
from urllib.parse import urlparse
import requests
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Error








# ===== Helper Function =====
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class BaseAPIView(APIView):
    def success_response(self, message="Your request Accepted", data=None, status_code=status.HTTP_200_OK):
        return Response(
            {"success": True, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )

    def error_response(self, message="Your request rejected", data=None, status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            {"success": False, "message": message, "status": status_code, "data": data or {}},
            status=status_code
        )

# ===== Signup =====
class SignupView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return self.success_response(
                "User created successfully. Please verify OTP.",
                data={"email": user.email}
            )
        return self.error_response("Signup failed.", data=serializer.errors)

class SignupOTPVerifyView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        otp = request.data.get("otp")
        if not otp:
            return self.error_response("OTP is required.")

        try:
            user = User.objects.get(otp=otp, otp_exp__gte=timezone.now(), otp_verified=False)
        except User.DoesNotExist:
            return self.error_response("Invalid or expired OTP.")

        user.otp_verified = True
        user.save()
        tokens = get_tokens_for_user(user)
        return self.success_response(
            "OTP verified successfully.",
            data={"tokens": tokens}
        )

class ChooseRoleAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = RoleSelectionSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.user_type:
                return self.error_response("Role already selected.")
            serializer.update(user, serializer.validated_data)
            return self.success_response("Role selected successfully.")
        return self.error_response("Role Selection Failed", data=serializer.errors)





# ===== Login =====
class LoginView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            user = authenticate(request, email=email, password=password)
            if user:
                if not user.user_type:
                    return self.error_response(
                        "Please choose your role first.",
                        status_code=status.HTTP_403_FORBIDDEN
                    )

                tokens = get_tokens_for_user(user)
                # ProfileView-এর মতো একই serializer ব্যবহার করে প্রোফাইল ডেটা নিন
                profile_data = ProfileSerializer(user, context={"request": request}).data

                return self.success_response(
                    "Login successful",
                    data={
                        "tokens": tokens,
                        "profile": profile_data,   # এখানে প্রোফাইল অ্যাড হল
                    }
                )
            return self.error_response(
                "Invalid email or password",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        return self.error_response(
            "Login Failed",
            data=serializer.errors
        )








# ===== Profile =====
class ProfileView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user, context={'request': request})
        return self.success_response(data=serializer.data)

    def put(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return self.success_response("Profile updated", data=serializer.data)
        return self.error_response("Profile updated failed", data=serializer.errors)

# ===== Password Reset =====
class PasswordResetRequestAPIView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            return self.success_response("OTP sent to email.", data={"email": serializer.validated_data["email"]})
        return self.error_response("OTP sent failed", data=serializer.errors)

class PasswordResetOTPVerifyView(BaseAPIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        otp = request.data.get("otp")
        if not otp:
            return self.error_response("OTP is required.")

        try:
            user = User.objects.get(otp=otp, otp_exp__gte=timezone.now(), otp_verified=False)
        except User.DoesNotExist:
            return self.error_response("Invalid or expired OTP.")

        user.otp_verified = True
        user.save()
        tokens = get_tokens_for_user(user)  # Access + Refresh token
        return self.success_response(
            "OTP verified successfully.",
            data={"tokens": tokens}
        )

class PasswordResetChangeAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetChangeSerializer(data=request.data)
        if serializer.is_valid():
            request.user.set_password(serializer.validated_data["new_password"])
            request.user.otp_verified = False
            request.user.otp = None
            request.user.otp_exp = None
            request.user.save()
            return self.success_response("Password reset successful.")
        return self.error_response("Password reset failed", data=serializer.errors)



class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": f"Logout failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        



# Authenticated endpoint: change current user's password with validation
class ChangePassword(BaseAPIView, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Password changed failed", data=serializer.errors)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return self.error_response("Old password does not match")

        user.set_password(new_password)
        user.save()
        return self.success_response("Password changed successfully")
    






# mapping content-type to extension (define somewhere central or keep this small mapping)
_CONTENTTYPE_TO_EXT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}

# Your ProfileSerializer should already exist
# from .serializers import ProfileSerializer

class GoogleLoginView(SocialLoginView, BaseAPIView):
    adapter_class = GoogleOAuth2Adapter
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        """
        Handle Google social login and return tokens + profile in the same
        response format as LoginView:
        {
          "success": True,
          "message": "Login successful",
          "status": 200,
          "data": {
            "tokens": { "refresh": "...", "access": "..." },
            "profile": { ...profile serializer data... }
          }
        }
        """
        try:
            # Let dj-rest-auth / allauth handle the oauth flow (creates/attaches socialaccount)
            super().post(request, *args, **kwargs)

            user = getattr(self, "user", None)
            if user is None:
                return self.error_response(
                    "User not available after social login.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # Safely read extra_data from socialaccount if available
            extra_data = {}
            try:
                sa = user.socialaccount_set.first()
                if sa:
                    extra_data = sa.extra_data or {}
            except Exception:
                extra_data = {}

            first_name = extra_data.get("given_name", "") or ""
            last_name = extra_data.get("family_name", "") or ""
            picture_url = extra_data.get("picture", None)

            combined_name = " ".join(filter(None, [first_name.strip(), last_name.strip()])).strip()
            if not combined_name:
                combined_name = extra_data.get("name") or user.name or user.email

            # Update user fields atomically
            with transaction.atomic():
                user.name = combined_name

                # Download & save profile picture only if user doesn't already have one
                if picture_url and (not getattr(user, "profile_pic", None)):
                    try:
                        r = requests.get(picture_url, timeout=5)
                        if r.status_code == 200 and r.content:
                            content_type = r.headers.get("content-type", "").split(";")[0].lower()
                            ext = _CONTENTTYPE_TO_EXT.get(content_type)

                            # fallback: extract extension from URL path
                            if not ext:
                                path = urlparse(picture_url).path
                                if "." in path:
                                    guessed = path.split(".")[-1].lower()
                                    if guessed in ("jpg", "jpeg", "png", "gif", "webp"):
                                        ext = guessed

                            if not ext:
                                ext = "jpg"

                            filename = urlparse(picture_url).path.split("/")[-1] or f"profile_{user.pk}.{ext}"
                            if not filename.lower().endswith("." + ext):
                                filename = f"{filename}.{ext}"

                            user.profile_pic.save(filename, ContentFile(r.content), save=False)
                    except requests.RequestException:
                        # ignore image download errors so login isn't blocked
                        pass

                # clear OTP / mark verified to avoid blocking social users with OTP flow
                user.otp = None
                user.otp_exp = None
                user.otp_verified = True

                user.save()

            # Create JWT tokens
            refresh = RefreshToken.for_user(user)
            tokens = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }

            # Use same ProfileSerializer as your LoginView / ProfileView
            profile_data = ProfileSerializer(user, context={"request": request}).data

            return self.success_response(
                "Login successful",
                data={
                    "tokens": tokens,
                    "profile": profile_data,
                }
            )

        except OAuth2Error as e:
            return self.error_response(
                "Failed to fetch Google user info. Token may be expired or invalid.",
                data={"detail": str(e)},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            return self.error_response(
                "Unexpected error during social login.",
                data={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
