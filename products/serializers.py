from rest_framework import serializers
from .models import Category, Product
from shops.serializers import ShopSerializer

class CategorySerializer(serializers.ModelSerializer):
    """Serializer برای دسته‌بندی"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'created_at']
        read_only_fields = ['slug', 'created_at']

class ProductListSerializer(serializers.ModelSerializer):
    """Serializer برای لیست محصولات (ساده‌تر)"""
    shop = ShopSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    price_in_toman = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'shop', 'category', 'price', 'price_in_toman',
            'stock', 'is_available', 'size', 'color', 'brand', 'material',
            'images', 'views', 'created_at'
        ]
        read_only_fields = ['views', 'created_at']
    
    def get_price_in_toman(self, obj):
        """تبدیل قیمت به تومان"""
        return obj.get_price_in_toman()

class ProductDetailSerializer(ProductListSerializer):
    """Serializer برای جزئیات محصول (کامل)"""
    is_in_stock = serializers.BooleanField(read_only=True)
    
    class Meta(ProductListSerializer.Meta):
        fields = ProductListSerializer.Meta.fields + ['description', 'is_in_stock']