from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrderViewSet

# urlpatterns = [
#     # path('create/', views.OrderCreateAPIView.as_view(), name='order-create'),
#     # path('track/', views.OrderTrackAPIView.as_view(), name='order-track'),
#     # path('shop-orders/', views.ShopOrderListAPIView.as_view(), name='shop-orders'),
# ]

app_name = 'orders'

router = DefaultRouter()
router.register(r'', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]

