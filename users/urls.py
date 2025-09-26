from django.urls import path
# from .views import UpdateStreakAPIView
from .views import SignupView, LoginView, LogoutView, ProfileView, ChangePassword, PasswordResetRequestAPIView, OTPVerificationAPIView, PasswordResetAPIView, DeleteAccountAPIView
from rest_framework_simplejwt.views import TokenRefreshView
from .views import GoogleLoginView, AppleLoginView




urlpatterns = [
    path('auth/signup/', SignupView.as_view(), name='signup'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/profile/', ProfileView.as_view(), name='profile'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('delete-account/', DeleteAccountAPIView.as_view(), name='delete-account'),

    # Password reset and change
    path("auth/change-password/", ChangePassword.as_view(), name="change_password"),
    path("auth/password-reset/request/", PasswordResetRequestAPIView.as_view(), name="password-reset-request"),
    path("auth/password-reset/verify-otp/", OTPVerificationAPIView.as_view(), name="password-reset-verify-otp"),
    path("auth/password-reset/change-password/", PasswordResetAPIView.as_view(), name="password-reset-change"),

    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),
    path('auth/apple/', AppleLoginView.as_view(), name='apple_login'),
]
