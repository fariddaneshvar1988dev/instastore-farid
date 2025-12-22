from rest_framework import generics, filters
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend  # این خط را اصلاح کردیم
from .models import Product, Category
from .serializers import ProductListSerializer, ProductDetailSerializer, CategorySerializer

class ProductListAPIView(generics.ListAPIView):
    """لیست محصولات یک فروشگاه"""
    serializer_class = ProductListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_available', 'size', 'color', 'brand']
    search_fields = ['name', 'description', 'brand', 'material']
    ordering_fields = ['price', 'created_at', 'views']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """فقط محصولات فروشگاه جاری"""
        shop = self.request.shop  # از middleware می‌آید
        return Product.objects.filter(
            shop=shop,
            is_available=True
        ).select_related('category', 'shop')

class ProductDetailAPIView(generics.RetrieveAPIView):
    """نمایش جزئیات یک محصول"""
    serializer_class = ProductDetailSerializer
    lookup_field = 'id'
    lookup_url_kwarg = 'product_id'
    
    def get_queryset(self):
        shop = self.request.shop
        return Product.objects.filter(shop=shop)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # افزایش تعداد بازدید
        instance.views += 1
        instance.save(update_fields=['views'])
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class CategoryListAPIView(generics.ListAPIView):
    """لیست دسته‌بندی‌های یک فروشگاه"""
    serializer_class = CategorySerializer
    
    def get_queryset(self):
        shop = self.request.shop
        # دسته‌بندی‌هایی که محصول فعال در این فروشگاه دارند
        return Category.objects.filter(
            products__shop=shop,
            products__is_available=True
        ).distinct()