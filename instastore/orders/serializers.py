from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem
from customers.models import Customer
from products.models import ProductVariant
import re

class OrderItemSerializer(serializers.ModelSerializer):
    """Serializer برای نمایش آیتم‌های سفارش"""
    product_name = serializers.CharField(read_only=True)
    size = serializers.CharField(read_only=True)
    color = serializers.CharField(read_only=True)
    
    # برای ورودی: آی‌دیِ واریانت (مثلاً ترکیب قرمز-XL) را می‌گیریم
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(),
        source='variant',
        write_only=True
    )
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'variant_id', 'product_name', 'size', 'color',
            'quantity', 'unit_price', 'total_price'
        ]
        read_only_fields = ['product_name', 'size', 'color', 'unit_price', 'total_price']

class OrderSerializer(serializers.ModelSerializer):
    """Serializer اصلی سفارش با قابلیت ثبت‌نام خودکار"""
    items = OrderItemSerializer(many=True, read_only=True)
    
    # ورودی‌های مخصوص ساخت سفارش (که در دیتابیس Order نیستند)
    customer_phone = serializers.CharField(write_only=True, required=True, max_length=15)
    items_data = serializers.ListField(child=serializers.DictField(), write_only=True, required=True)
    
    class Meta:
        model = Order
        fields = [
            'order_id', 'status', 'payment_method', 'total_amount',
            'customer_phone', 'customer_name', 'shipping_address', 
            'items', 'items_data', 'created_at'
        ]
        read_only_fields = ['order_id', 'status', 'total_amount', 'created_at']

    def validate_customer_phone(self, value):
        """اعتبارسنجی ساده شماره تماس در سفارش"""
        phone = re.sub(r'\D', '', value)
        if len(phone) < 10:
            raise serializers.ValidationError("شماره تماس نامعتبر است.")
        return phone

    def create(self, validated_data):
        """
        منطق ثبت سفارش:
        ۱. جدا کردن داده‌های اضافی (items_data)
        ۲. پیدا کردن یا ساختن مشتری
        ۳. تشخیص فروشگاه
        ۴. ثبت سفارش
        """
        # مهم: این فیلدها را از دیکشنری خارج می‌کنیم تا به مدل Order پاس داده نشوند
        items_data = validated_data.pop('items_data')
        phone = validated_data.pop('customer_phone')
        full_name = validated_data.get('customer_name', '')
        
        request = self.context.get('request')
        
        # --- ۱. مدیریت مشتری (Invisible Registration) ---
        if request and request.user.is_authenticated:
            # اگر لاگین است
            if hasattr(request.user, 'customer_profile'):
                customer = request.user.customer_profile
            else:
                customer = Customer.objects.create(
                    user=request.user, phone_number=phone, full_name=full_name
                )
        else:
            # اگر مهمان است: پیدا کن یا بساز
            customer, created = Customer.objects.get_or_create(
                phone_number=phone,
                defaults={'full_name': full_name}
            )
            if not created and not customer.full_name and full_name:
                customer.full_name = full_name
                customer.save()

        # --- ۲. تشخیص فروشگاه (رفع باگ IntegrityError) ---
        if not items_data:
            raise serializers.ValidationError("سبد خرید نمی‌تواند خالی باشد.")
            
        first_variant_id = items_data[0].get('variant_id')
        try:
            first_variant = ProductVariant.objects.get(id=first_variant_id)
            shop = first_variant.product.shop
        except ProductVariant.DoesNotExist:
            raise serializers.ValidationError(f"محصول با شناسه {first_variant_id} وجود ندارد.")

        # --- ۳. ثبت سفارش (اتمیک) ---
        with transaction.atomic():
            # ایجاد سفارش با اتصال به فروشگاه و مشتری
            order = Order.objects.create(
                shop=shop,
                customer=customer, 
                customer_phone=phone, 
                **validated_data
            )
            
            for item in items_data:
                variant_id = item.get('variant_id')
                quantity = item.get('quantity', 1)
                
                try:
                    variant = ProductVariant.objects.select_for_update().get(id=variant_id)
                except ProductVariant.DoesNotExist:
                    raise serializers.ValidationError(f"محصول با شناسه {variant_id} وجود ندارد.")

                if variant.product.shop != shop:
                    raise serializers.ValidationError("امکان ثبت سفارش همزمان از چند فروشگاه وجود ندارد.")

                if variant.stock < quantity:
                    raise serializers.ValidationError(f"موجودی '{variant.product.name}' کافی نیست.")
                
                # ایجاد آیتم
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=quantity
                )
                
                # کسر موجودی (اختیاری - اگر می‌خواهید انبار کم شود این خط را از کامنت درآورید)
                variant.stock -= quantity
                variant.save()
            
            # محاسبه قیمت نهایی
            order.calculate_totals()
            
            # آپدیت آمار مشتری
            customer.update_stats(order.total_amount)
            
        return order