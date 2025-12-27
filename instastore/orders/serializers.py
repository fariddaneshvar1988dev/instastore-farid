from rest_framework import serializers
from .models import Order, OrderItem
from shops.serializers import ShopSerializer
from customers.serializers import CustomerSerializer
from products.serializers import ProductListSerializer
from products.models import Product

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer برای آیتم‌های سفارش"""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',
        write_only=True,
        required=True
    )
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_id', 'product_name',
            'product_price', 'quantity', 'total_price'
        ]
        read_only_fields = ['product_name', 'product_price', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    """Serializer برای سفارش"""
    shop = ShopSerializer(read_only=True)
    customer = CustomerSerializer(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display_fa', read_only=True)
    
    # فیلدهای write-only برای ایجاد سفارش
    customer_phone = serializers.CharField(write_only=True, required=True)
    items_data = serializers.JSONField(write_only=True, required=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_id', 'shop', 'customer', 'status', 'status_display',
            'payment_method', 'payment_status', 'subtotal', 'shipping_cost',
            'discount', 'total_amount', 'customer_phone', 'customer_name',
            'shipping_address', 'customer_notes', 'tracking_code',
            'estimated_delivery', 'delivered_at', 'created_at', 'updated_at',
            'items', 'items_data'
        ]
        read_only_fields = [
            'order_id', 'status', 'payment_status', 'subtotal',
            'total_amount', 'customer_name', 'created_at', 'updated_at',
            'delivered_at'
        ]
    
    def validate_items_data(self, value):
        """اعتبارسنجی آیتم‌های سفارش"""
        if not isinstance(value, list):
            raise serializers.ValidationError("items_data باید یک لیست باشد")
        
        if len(value) == 0:
            raise serializers.ValidationError("سفارش باید حداقل یک آیتم داشته باشد")
        
        for item in value:
            if 'product_id' not in item or 'quantity' not in item:
                raise serializers.ValidationError("هر آیتم باید product_id و quantity داشته باشد")
            
            if not isinstance(item['quantity'], int) or item['quantity'] <= 0:
                raise serializers.ValidationError("quantity باید عدد مثبت باشد")
        
        return value