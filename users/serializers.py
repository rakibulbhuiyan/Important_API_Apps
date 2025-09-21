from attr import attrs
from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.utils.timezone import now, timedelta
from .models import *
from apps.browse.models import Proffessional, About

class SignupSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(write_only=True)
    last_name = serializers.CharField(write_only=True)
    profile_pic = serializers.ImageField(write_only=True, required=False)
    confirm_password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=User.ROLE, required=False) 

    class Meta:
        model = User
        fields = [
            'email', 'password', 'confirm_password',
            'first_name', 'last_name', 'profile_pic', 'role'
        ]
        extra_kwargs = {'password': {'write_only': True}}

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        first_name = validated_data.pop('first_name')
        last_name = validated_data.pop('last_name')
        profile_pic = validated_data.pop('profile_pic', None)
        role = validated_data.pop('role', 'user')  # Pop role from validated_data
        validated_data.pop('confirm_password')

        # Create User with role explicitly
        user = User.objects.create_user(**validated_data, role=role)

        # Create Profile
        Profile.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            profile_pic=profile_pic,
        )

        # If professional → create Professional & About
        if role == "professional":
            professional = Proffessional.objects.create(
                user=user,
                name=f"{first_name} {last_name}"
            )
            About.objects.create(
                professional=professional,
                educations_certifications=[],
                languages=[],
                specializations=[]
            )

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        user = authenticate(email=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("User is inactive.")

        refresh = RefreshToken.for_user(user)
        return {
            'id': user.id,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'role': user.role,  # DB theke role return
        }




class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Profile
        fields = [
            'email',
            'first_name',
            'last_name',
            'profile_pic',
            'phone_number',
            'bio',
        ]

    def update(self, instance, validated_data):
        # Update nested user email if needed (but here we keep it read_only)
        user_data = validated_data.pop('user', {})
        email = user_data.get('email')
        if email:
            instance.user.email = email
            instance.user.save()

        return super().update(instance, validated_data)
    




class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data



class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        # Generate OTP and send via email
        user.generate_otp()
        print(user.otp)
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