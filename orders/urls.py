from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.OrderCreateAPIView.as_view(), name='order-create'),
    path('track/', views.OrderTrackAPIView.as_view(), name='order-track'),
    path('shop-orders/', views.ShopOrderListAPIView.as_view(), name='shop-orders'),
]