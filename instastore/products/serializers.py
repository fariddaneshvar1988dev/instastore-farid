# products/serializers.py
from rest_framework import serializers
from .models import Category, Product, ProductVariant, ProductImage
from shops.serializers import ShopSerializer

class CategorySerializer(serializers.ModelSerializer):
    """Serializer برای دسته‌بندی"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at']
        read_only_fields = ['slug', 'created_at']

class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer برای تصاویر محصول"""
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'created_at']
        read_only_fields = ['created_at']

class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer برای تنوع محصول"""
    final_price = serializers.DecimalField(max_digits=12, decimal_places=0, read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = ['id', 'size', 'color', 'stock', 'price_adjustment', 'final_price']
        read_only_fields = ['final_price']

class ProductListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست محصولات (ساده‌تر)"""
    shop = ShopSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    main_image = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'shop', 'category', 'base_price',
            'total_stock', 'is_active', 'brand', 'material',
            'main_image', 'views', 'created_at'
        ]
        read_only_fields = ['views', 'created_at', 'total_stock', 'main_image']
    
    def get_main_image(self, obj):
        if obj.images.exists():
            return obj.images.first().image.url
        return None

class ProductDetailSerializer(ProductListSerializer):
    """Serializer برای جزئیات محصول (کامل)"""
    images = ProductImageSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + [
            'description', 'is_available', 'images', 'variants'
        ]