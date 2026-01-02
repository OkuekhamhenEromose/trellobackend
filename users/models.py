from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

# Custom User Model (optional but better)
class CustomUser(AbstractUser):
    email_verified = models.BooleanField(default=False)
    
    class Meta:
        swappable = 'AUTH_USER_MODEL'

# Email Verification Token Model
class EmailVerificationToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at

# Profile Model
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    fullname = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.fullname or self.user.username

# Temporary Registration Data (store email before full registration)
class TemporaryRegistration(models.Model):
    email = models.EmailField(unique=True)
    verification_code = models.CharField(max_length=6, blank=True, null=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_verified = models.BooleanField(default=False)
    
    def is_valid(self):
        return not self.is_verified and timezone.now() < self.expires_at