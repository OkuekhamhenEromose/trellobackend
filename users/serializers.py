from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Profile, EmailVerificationToken, TemporaryRegistration
from django.utils import timezone
from datetime import timedelta
import uuid

class EmailOnlySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    
    def validate_email(self, value):
        # Check if email is already registered
        if User.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    verification_code = serializers.CharField(max_length=6, required=False)
    token = serializers.UUIDField(required=False)
    
    def validate(self, data):
        email = data.get('email')
        
        try:
            temp_reg = TemporaryRegistration.objects.get(
                email=email,
                expires_at__gt=timezone.now()
            )
        except TemporaryRegistration.DoesNotExist:
            raise serializers.ValidationError("Verification expired or invalid.")
        
        # If verification code is provided, validate it
        verification_code = data.get('verification_code')
        if verification_code:
            if temp_reg.verification_code != verification_code:
                raise serializers.ValidationError("Invalid verification code.")
        
        # If token is provided, validate it
        token = data.get('token')
        if token:
            try:
                if temp_reg.token != token:
                    raise serializers.ValidationError("Invalid verification token.")
            except ValueError:
                raise serializers.ValidationError("Invalid token format.")
        
        data['temp_reg'] = temp_reg
        return data

class CompleteRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    token = serializers.UUIDField(required=True)
    fullname = serializers.CharField(required=True, max_length=255)
    username = serializers.CharField(required=True, max_length=150)
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = ['email', 'token', 'fullname', 'username', 'password', 'password2']
    
    def validate(self, data):
        email = data.get('email')
        token = data.get('token')
        password = data.get('password')
        password2 = data.get('password2')
        
        # Check passwords match
        if password != password2:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            raise serializers.ValidationError({"email": "Enter a valid email address."})
        
        # Check if email already registered
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
        
        # Check if username already exists
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({"username": "This username is already taken."})
        
        # Verify temporary registration
        try:
            temp_reg = TemporaryRegistration.objects.get(
                email=email,
                token=token,
                expires_at__gt=timezone.now(),
                is_verified=True
            )
            data['temp_reg'] = temp_reg
        except TemporaryRegistration.DoesNotExist:
            raise serializers.ValidationError({"token": "Invalid or expired verification token."})
        
        return data
    
    def create(self, validated_data):
        # Create user
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=True
        )
        
        # Create profile
        Profile.objects.create(
            user=user,
            fullname=validated_data['fullname']
        )
        
        # Mark temporary registration as used
        temp_reg = validated_data['temp_reg']
        temp_reg.delete()  # Remove after successful registration
        
        # Create email verification token (for later verification if needed)
        expires_at = timezone.now() + timedelta(hours=24)
        EmailVerificationToken.objects.create(
            user=user,
            expires_at=expires_at
        )
        
        return user

class UserSerializer(serializers.ModelSerializer):
    profile_fullname = serializers.CharField(source='profile.fullname', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile_fullname']

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    username = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, data):
        email = data.get('email')
        username = data.get('username')
        
        if not email and not username:
            raise serializers.ValidationError("Either email or username is required.")
        
        return data

class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Profile
        fields = ['fullname', 'phone', 'email', 'username']