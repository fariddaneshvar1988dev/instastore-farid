from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProductListAPIView.as_view(), name='product-list'),
    path('categories/', views.CategoryListAPIView.as_view(), name='category-list'),
    path('<int:product_id>/', views.ProductDetailAPIView.as_view(), name='product-detail'),
]