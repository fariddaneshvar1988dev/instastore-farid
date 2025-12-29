from rest_framework import serializers
from .models import Customer
import re

class CustomerSerializer(serializers.ModelSerializer):
    """Serializer کامل برای نمایش و ویرایش مشتری"""
    # این فیلد را required=False می‌کنیم چون ممکن است در آپدیت ارسال نشود
    phone_number = serializers.CharField(max_length=15, required=False)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'phone_number', 'full_name', 'default_address',
            'is_active', 'total_orders', 'total_spent',
            'created_at', 'last_seen'
        ]
        read_only_fields = [
            'id', 'is_active', 'total_orders', 'total_spent',
            'created_at', 'last_seen'
        ]
    
    def validate_phone_number(self, value):
        """اعتبارسنجی شماره تلفن ایران"""
        # حذف فاصله و کاراکترهای غیرعددی
        phone = re.sub(r'\D', '', value)
        
        # بررسی طول شماره (با احتساب 0 اول یا 98)
        if len(phone) == 10 and not value.startswith('0'):
             phone = '0' + phone # افزودن صفر اگر کاربر یادش رفته
        
        if len(phone) != 11:
            raise serializers.ValidationError("شماره تلفن باید ۱۱ رقم باشد (مثال: 09123456789)")
        
        if not phone.startswith('09'):
            raise serializers.ValidationError("شماره تلفن معتبر نیست.")
        
        return phone

class CustomerCreateSerializer(serializers.ModelSerializer):
    """Serializer برای ایجاد مشتری جدید"""
    class Meta:
        model = Customer
        fields = ['phone_number', 'full_name']
    
    def create(self, validated_data):
        """ایجاد مشتری جدید - اگر وجود داشت، برگرداندن همان"""
        phone_number = validated_data['phone_number']
        customer, created = Customer.objects.get_or_create(
            phone_number=phone_number,
            defaults=validated_data
        )
        return customer