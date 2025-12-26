from django.urls import path
from . import views

urlpatterns = [
    
    # path('create/', views.ShopCreateAPIView.as_view(), name='shop-create'),
    # path('my-shop/', views.CurrentUserShopAPIView.as_view(), name='my-shop'),
    # path('<slug:slug>/', views.ShopDetailAPIView.as_view(), name='shop-detail'),
    path('register/', views.RegisterSellerAPIView.as_view(), name='register'),
]