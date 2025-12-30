from rest_framework import serializers
from django.db import transaction
from .models import Order, OrderItem
from customers.models import Customer
from products.models import ProductVariant
import re

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(read_only=True)
    size = serializers.CharField(read_only=True)
    color = serializers.CharField(read_only=True)
    
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
    items = OrderItemSerializer(many=True, read_only=True)
    customer_phone = serializers.CharField(write_only=True, required=True, max_length=20)
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
        """
        تبدیل اعداد فارسی/عربی به انگلیسی و اعتبارسنجی
        """
        if not value:
            raise serializers.ValidationError("شماره تماس الزامی است.")
            
        # تبدیل اعداد فارسی و عربی به انگلیسی
        translation_table = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')
        value = value.translate(translation_table)
        
        # حذف هر چیزی غیر از عدد
        phone = re.sub(r'\D', '', value)
        
        if len(phone) < 10:
            raise serializers.ValidationError("شماره تماس معتبر نیست (حداقل ۱۰ رقم).")
        
        return phone

    def create(self, validated_data):
        items_data = validated_data.pop('items_data')
        phone = validated_data.pop('customer_phone')
        full_name = validated_data.get('customer_name', '') or 'کاربر مهمان'
        
        request = self.context.get('request')
        
        # ۱. مدیریت مشتری
        if request and request.user.is_authenticated:
            if hasattr(request.user, 'customer_profile'):
                customer = request.user.customer_profile
            else:
                customer = Customer.objects.create(
                    user=request.user, phone_number=phone, full_name=full_name
                )
        else:
            customer, created = Customer.objects.get_or_create(
                phone_number=phone,
                defaults={'full_name': full_name}
            )
            if not created and not customer.full_name:
                customer.full_name = full_name
                customer.save()

        # ۲. اعتبارسنجی اولیه سبد خرید
        if not items_data:
            raise serializers.ValidationError({"items_data": "سبد خرید نمی‌تواند خالی باشد."})
            
        first_variant_id = items_data[0].get('variant_id')
        try:
            first_variant = ProductVariant.objects.get(id=first_variant_id)
            shop = first_variant.product.shop
        except (ProductVariant.DoesNotExist, TypeError):
            raise serializers.ValidationError("محصول انتخاب شده نامعتبر است.")

        # ۳. ثبت اتمیک سفارش
        with transaction.atomic():
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
                
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    quantity=quantity
                )
                
                # کسر موجودی
                from django.db.models import F
                variant.stock = F('stock') - quantity
                variant.save()
            
            order.calculate_totals()
            customer.update_stats(order.total_amount)
            
        return order