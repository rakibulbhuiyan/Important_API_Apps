from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import SignupSerializer, LoginSerializer, ProfileSerializer, ChangePasswordSerializer, PasswordResetRequestSerializer, PasswordResetChangeSerializer
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone



# Base API view providing standardized success/error response helpers
class BaseAPIView(APIView):
    # Return a normalized success payload with optional data
    def success_response(self, message="Your request Accepted", data=None, status_code= status.HTTP_200_OK):
        return Response(
            {
            "success": True,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )
    # Return a normalized error payload with optional serializer errors
    def error_response(self, message="Your request rejected", data=None, status_code= status.HTTP_400_BAD_REQUEST):
        return Response(
            {
            "success": False,
            "message": message,
            "status": status_code,
            "data": data or {}
            },
            status=status_code )  



# ===== Helper Function =====
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }




# # Public endpoint: handle user registration via SignupSerializer
# class SignupView(BaseAPIView):
#     def post(self, request):
#         serializer = SignupSerializer(data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return self.success_response("User created successfully.", status_code=status.HTTP_201_CREATED)
#         return self.error_response("Signup failed.", data=serializer.errors)



# # Public endpoint: authenticate user and return token payload from LoginSerializer
# class LoginView(BaseAPIView):
#     def post(self, request):
#         serializer = LoginSerializer(data=request.data)
#         if serializer.is_valid():
#             return self.success_response("Login successful.", data=serializer.validated_data)
#         return self.error_response("Login failed.", data=serializer.errors)



from rest_framework.exceptions import APIException

class SignupView(BaseAPIView):
    def post(self, request):
        try:
            serializer = SignupSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return self.success_response(
                    "User created successfully.",
                    status_code=status.HTTP_201_CREATED
                )
            return self.error_response(
                "Signup failed.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # log the error if you have logging enabled
            return self.error_response(
                "An unexpected error occurred during signup.",
                data={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LoginView(BaseAPIView):
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            if serializer.is_valid():
                # user = request.user
                # user = serializer.validated_data.get("user")
                # create_notification(user, "Login", "User Login Successfully")
                return self.success_response(
                    "Login successful.",
                    data=serializer.validated_data,
                    status_code=status.HTTP_200_OK
                )
            return self.error_response(
                "Login failed.",
                data=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            # log the error if you have logging enabled
            return self.error_response(
                "An unexpected error occurred during login.",
                data={"detail": str(e)},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




# Authenticated endpoint: blacklist provided refresh token to log out
class LogoutView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            token = RefreshToken(refresh_token)
            token.blacklist()
            return self.success_response("Successfully logged out.", status_code=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return self.error_response("Invalid refresh token")


# Authenticated endpoint: retrieve/update current user's profile
class ProfileView(BaseAPIView):
    permission_classes = [permissions.IsAuthenticated]

    # Return serialized profile for the current user
    def get(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return self.success_response("Profile fetched successfully.", data=serializer.data)

    # Partially update the profile; optionally trigger a reminder notification
    def put(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return self.success_response("Profile updated successfully.", data=serializer.data)
        return self.error_response("Profile update failed.", data=serializer.errors)
    

# Authenticated endpoint: change current user's password with validation
class ChangePassword(BaseAPIView, generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def put(self, request):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response("Validation error", data=serializer.errors)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(old_password):
            return self.error_response("Old password does not match")

        user.set_password(new_password)
        user.save()
        return self.success_response("Password changed successfully")


# Public endpoint: request a password reset (sends OTP to email)
class PasswordResetRequestAPIView(BaseAPIView):
    permission_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            return self.success_response("OTP sent to email.")
        return self.error_response("Validation error", serializer.errors)





# Public endpoint: verify OTP for password reset flow
class OTPVerificationAPIView(BaseAPIView):
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


# Public endpoint: finalize password reset using a valid OTP/token
class PasswordResetAPIView(BaseAPIView):
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
        return self.error_response("Validation error", data=serializer.errors)



# Authenticated endpoint: permanently delete the current user's account
class DeleteAccountAPIView(BaseAPIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()  # Permanent Delete
        return self.success_response("Your account has been deleted.")
