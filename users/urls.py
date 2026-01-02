from django.urls import path
from . import views

urlpatterns = [
    # New Trello-style registration flow
    path('register/start/', views.StartRegistrationView.as_view(), name='register-start'),
    path('register/verify/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('register/complete/', views.CompleteRegistrationView.as_view(), name='register-complete'),
    
    # Email checking
    path('check-email/', views.CheckEmailView.as_view(), name='check-email'),
    
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Optional: Resend verification email
    path('resend-verification/', views.StartRegistrationView.as_view(), name='resend-verification'),
]