# orders/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'orders', views.OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    
    # مسیرهای اضافی
    path('shop-orders/<int:shop_id>/', views.ShopOrderViewSet.as_view({'get': 'list'}), name='shop-orders-list'),
    path('shop-orders/<int:shop_id>/<int:pk>/', views.ShopOrderViewSet.as_view({'get': 'retrieve'}), name='shop-orders-detail'),
]