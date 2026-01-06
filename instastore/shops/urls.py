# shops/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterSellerAPIView.as_view(), name='register'),
]