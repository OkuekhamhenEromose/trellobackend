from django.shortcuts import redirect, get_object_or_404
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import permission_classes
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    EmailOnlySerializer, 
    VerifyEmailSerializer, 
    CompleteRegistrationSerializer,
    UserSerializer, 
    LoginSerializer, 
    ProfileSerializer
)
from .models import Profile, TemporaryRegistration, EmailVerificationToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from datetime import timedelta
import random
import string
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class StartRegistrationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 1: User enters email only
        """
        serializer = EmailOnlySerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            # Delete any existing temporary registrations for this email
            TemporaryRegistration.objects.filter(email=email).delete()
            
            # Generate verification code (6 digits)
            verification_code = ''.join(random.choices(string.digits, k=6))
            
            # Create temporary registration
            expires_at = timezone.now() + timedelta(minutes=30)
            temp_reg = TemporaryRegistration.objects.create(
                email=email,
                verification_code=verification_code,
                expires_at=expires_at
            )
            
            # Send verification email
            try:
                self._send_verification_email(email, verification_code, temp_reg.token)
            except Exception as e:
                # Log error but continue (email might fail)
                print(f"Email sending failed: {e}")
            
            return Response({
                'message': 'Verification email sent',
                'email': email,
                'token': str(temp_reg.token),
                'expires_at': expires_at
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_verification_email(self, email, verification_code, token):
        subject = "Verify Your Email - Trello Clone"
        
        # Create verification URL
        verification_url = f"{settings.FRONTEND_URL}/verify-email?email={email}&token={token}"
        
        # HTML email content
        html_message = render_to_string('users/email_verification.html', {
            'email': email,
            'verification_code': verification_code,
            'verification_url': verification_url,
            'site_name': 'Trello Clone'
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 2: Verify email with code or token
        """
        serializer = VerifyEmailSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            temp_reg = serializer.validated_data['temp_reg']
            
            # Mark as verified
            temp_reg.is_verified = True
            temp_reg.save()
            
            return Response({
                'message': 'Email verified successfully',
                'email': email,
                'token': str(temp_reg.token),
                'verified': True
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self, request):
        """
        Verify email via token in URL (for email link clicks)
        """
        email = request.GET.get('email')
        token = request.GET.get('token')
        
        if not email or not token:
            return Response(
                {'error': 'Email and token are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            temp_reg = TemporaryRegistration.objects.get(
                email=email,
                token=token,
                expires_at__gt=timezone.now()
            )
            
            # Mark as verified
            temp_reg.is_verified = True
            temp_reg.save()
            
            # Redirect to frontend registration page
            return Response({
                'message': 'Email verified successfully',
                'email': email,
                'token': str(temp_reg.token),
                'verified': True,
                'redirect_url': f"{settings.FRONTEND_URL}/register?email={email}&token={token}"
            })
            
        except TemporaryRegistration.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired verification link'},
                status=status.HTTP_400_BAD_REQUEST
            )

class CompleteRegistrationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Step 3: Complete registration with full details
        """
        serializer = CompleteRegistrationSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Send welcome email
            self._send_welcome_email(user.email, user.profile.fullname)
            
            return Response({
                'message': 'Registration completed successfully',
                'user': UserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_welcome_email(self, email, fullname):
        subject = "Welcome to Trello Clone!"
        
        html_message = render_to_string('users/welcome_email.html', {
            'fullname': fullname,
            'site_name': 'Trello Clone'
        })
        
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=True,  # Don't fail registration if email fails
        )

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            username = serializer.validated_data.get('username')
            password = serializer.validated_data['password']
            
            # Try to authenticate by email or username
            if email:
                try:
                    user = User.objects.get(email=email)
                    username = user.username
                except User.DoesNotExist:
                    return Response(
                        {'error': 'Invalid email or password'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if not user.is_active:
                    return Response(
                        {'error': 'Account is disabled'},
                        status=status.HTTP_401_UNAUTHORIZED
                    )
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                # Django session login (optional)
                login(request, user)
                
                return Response({
                    'message': 'Login successful',
                    'user': UserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }, status=status.HTTP_200_OK)
            
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            logout(request)
            return Response(
                {'message': 'Logout successful'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = Profile.objects.create(user=request.user)
            serializer = ProfileSerializer(profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def put(self, request):
        try:
            profile = request.user.profile
            serializer = ProfileSerializer(profile, data=request.data, partial=True)
            
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Profile.DoesNotExist:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CheckEmailView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Check if email is available for registration
        """
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if email exists and is active
        email_exists = User.objects.filter(email=email, is_active=True).exists()
        
        return Response({
            'email': email,
            'available': not email_exists,
            'exists': email_exists
        }, status=status.HTTP_200_OK)