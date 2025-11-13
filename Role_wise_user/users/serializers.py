from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from rest_framework.exceptions import ValidationError

User = get_user_model()

# ===== Signup =====
class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['name', 'email', 'password', 'confirm_password']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', "")
        )
        user.generate_otp()
        send_mail(
            "Signup OTP",
            f"Your OTP is {user.otp}",
            "support@softvencefsd.xyz",
            [user.email],
            fail_silently=False,
        )
        return user

# ===== Login =====
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

# ===== Profile =====
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'email', 'profile_pic', 'user_type', 'is_active', 'youtube_link', 'instagram_link', 'tiktok_link']

# ===== Role =====
class RoleSelectionSerializer(serializers.Serializer):
    user_type = serializers.ChoiceField(choices=User.USER_TYPE_CHOICES)

    def update(self, instance, validated_data):
        instance.user_type = validated_data['user_type']
        instance.save()
        return instance

# ===== Password Reset =====
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        user.generate_otp()
        send_mail(
            "Password Reset OTP",
            f"Your OTP for password reset is {user.otp}",
            "support@softvencefsd.xyz",
            [user.email],
            fail_silently=False,
        )
        return value

class PasswordResetChangeSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data




class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data