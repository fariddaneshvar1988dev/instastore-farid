from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.CustomerProfileAPIView.as_view(), name='customer-profile'),
    path('send-otp/', views.SendOTPAPIView.as_view(), name='send-otp'),
    path('verify-otp/', views.VerifyOTPAPIView.as_view(), name='verify-otp'),
]