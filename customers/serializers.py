from rest_framework import serializers
from .models import Customer
import re

class CustomerSerializer(serializers.ModelSerializer):
    """Serializer برای مشتری"""
    phone_number = serializers.CharField(max_length=15, required=True)
    
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
        """اعتبارسنجی شماره تلفن"""
        # حذف فاصله و کاراکترهای غیرعددی
        phone = re.sub(r'\D', '', value)
        
        # بررسی طول شماره
        if len(phone) != 11:
            raise serializers.ValidationError("شماره تلفن باید ۱۱ رقم باشد")
        
        # بررسی شروع با ۰۹
        if not phone.startswith('09'):
            raise serializers.ValidationError("شماره تلفن باید با ۰۹ شروع شود")
        
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