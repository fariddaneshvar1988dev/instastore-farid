# shops/serializers.py
from rest_framework import serializers
from .models import Shop, Plan
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer برای کاربر"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class PlanSerializer(serializers.ModelSerializer):
    """Serializer برای پلن"""
    class Meta:
        model = Plan
        fields = ['id', 'name', 'code', 'description', 'price', 'days', 
                 'max_products', 'max_orders_per_month', 'is_active']
        read_only_fields = ['id']

class ShopSerializer(serializers.ModelSerializer):
    """Serializer برای فروشگاه"""
    user = UserSerializer(read_only=True)
    current_plan = PlanSerializer(read_only=True)
    is_subscription_active = serializers.BooleanField(read_only=True)
    remaining_days = serializers.IntegerField(read_only=True)
    
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Shop
        fields = [
            'id', 'user', 'user_id', 'instagram_username', 
            'shop_name', 'slug', 'bio', 'phone_number',
            'address', 'logo', 'is_active', 'enable_cod',
            'enable_card_to_card', 'card_owner_name', 'card_number',
            'shaba_number', 'enable_online_payment', 'zarinpal_merchant_id',
            'current_plan', 'plan_started_at', 'plan_expires_at',
            'is_subscription_active', 'remaining_days',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 
                           'plan_started_at', 'plan_expires_at',
                           'is_subscription_active', 'remaining_days']
    
    def validate_instagram_username(self, value):
        """اعتبارسنجی نام کاربری اینستاگرام"""
        if value and not value.startswith('@'):
            value = '@' + value
        return value.lower() if value else value