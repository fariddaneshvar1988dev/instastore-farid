# orders/serializers.py
from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from .models import Order, OrderItem
from shops.models import Shop
from products.models import ProductVariant
import re

User = get_user_model()

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    variant_display = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()
    
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        source='variant',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'variant_id', 'product', 'variant', 
            'product_name', 'variant_display',
            'quantity', 'price', 'total_price'
        ]
        read_only_fields = ['id', 'product', 'variant', 'product_name', 
                           'variant_display', 'price', 'total_price']
    
    def get_variant_display(self, obj):
        if obj.variant:
            return str(obj.variant)
        return "بدون تنوع"
    
    def get_total_price(self, obj):
        return obj.price * obj.quantity if obj.price else 0

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    shop_name = serializers.CharField(source='shop.name', read_only=True)
    
    # فیلدهای write-only برای ایجاد سفارش
    items_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )
    shop_id = serializers.PrimaryKeyRelatedField(
        queryset=Shop.objects.all(),
        source='shop',
        write_only=True
    )
    
    class Meta:
        model = Order
        fields = [
            'id', 'shop', 'shop_id', 'shop_name', 'user',
            'full_name', 'phone_number', 'address', 'postal_code',
            'city', 'province', 'status', 'payment_method',
            'is_paid', 'total_price', 'shipping_method',
            'shipping_cost', 'tracking_code', 'notes',
            'items', 'items_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'shop_name', 'total_price', 'is_paid', 
            'status', 'created_at', 'updated_at',
            'paid_at', 'shipped_at', 'delivered_at'
        ]

    def validate_phone_number(self, value):
        """اعتبارسنجی و نرمال‌سازی شماره تلفن"""
        if not value:
            raise serializers.ValidationError("شماره تماس الزامی است.")
        
        # تبدیل اعداد فارسی و عربی به انگلیسی
        translation_table = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
        value = value.translate(translation_table)
        
        # حذف هر چیزی غیر از عدد
        phone = re.sub(r'\D', '', value)
        
        if len(phone) < 10:
            raise serializers.ValidationError("شماره تماس معتبر نیست (حداقل ۱۰ رقم).")
        
        # اضافه کردن پیش‌شماره ایران اگر نیاز است
        if phone.startswith('0') and len(phone) == 11:
            return phone
        elif len(phone) == 10:
            return '0' + phone
        elif phone.startswith('98'):
            return '0' + phone[2:]
        elif phone.startswith('+98'):
            return '0' + phone[3:]
        
        return phone

    def create(self, validated_data):
        request = self.context.get('request')
        items_data = validated_data.pop('items_data', [])
        
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("برای ثبت سفارش باید وارد شوید.")
        
        # ایجاد سفارش
        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                **validated_data
            )
            
            # افزودن اقلام سفارش
            total_price = 0
            for item_data in items_data:
                variant_id = item_data.get('variant_id')
                quantity = item_data.get('quantity', 1)
                
                try:
                    variant = ProductVariant.objects.select_for_update().get(id=variant_id)
                except ProductVariant.DoesNotExist:
                    raise serializers.ValidationError(f"تنوع محصول با شناسه {variant_id} وجود ندارد.")
                
                # بررسی موجودیت محصول
                if variant.stock < quantity:
                    raise serializers.ValidationError(
                        f"موجودی محصول '{variant.product.name}' کافی نیست. "
                        f"موجودی: {variant.stock}، درخواستی: {quantity}"
                    )
                
                # بررسی اینکه محصول متعلق به فروشگاه سفارش است
                if variant.product.shop_id != validated_data['shop'].id:
                    raise serializers.ValidationError(
                        f"محصول '{variant.product.name}' متعلق به فروشگاه انتخابی نیست."
                    )
                
                # ایجاد آیتم سفارش
                order_item = OrderItem.objects.create(
                    order=order,
                    product=variant.product,
                    variant=variant,
                    price=variant.final_price,
                    quantity=quantity
                )
                
                # کسر از موجودی
                variant.stock -= quantity
                variant.save()
                
                total_price += order_item.price * order_item.quantity
            
            # محاسبه قیمت کل
            order.total_price = total_price + (order.shipping_cost or 0)
            order.save()
            
        return order

class OrderStatusUpdateSerializer(serializers.Serializer):
    """سریالایزر برای به‌روزرسانی وضعیت"""
    status = serializers.ChoiceField(choices=Order.STATUS_CHOICES)
    
    def update(self, instance, validated_data):
        instance.status = validated_data['status']
        instance.save()
        return instance

class AdminOrderSerializer(OrderSerializer):
    """سریالایزر برای ادمین - دسترسی کامل"""
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ['user_email', 'user_username']