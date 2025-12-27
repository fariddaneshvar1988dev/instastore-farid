from rest_framework import serializers
from .models import Shop
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    """Serializer برای کاربر"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ShopSerializer(serializers.ModelSerializer):
    """Serializer برای فروشگاه"""
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='user',
        write_only=True
    )
    
    class Meta:
        model = Shop
        fields = [
            'id', 'user', 'user_id', 'instagram_username', 
            'shop_name', 'slug', 'bio', 'phone_number', 
            'email', 'address', 'is_active', 'created_at', 
            'updated_at', 'get_absolute_url'
        ]
        read_only_fields = ['slug', 'created_at', 'updated_at', 'get_absolute_url']
    
    def validate_instagram_username(self, value):
        """اعتبارسنجی نام کاربری اینستاگرام"""
        if not value.startswith('@'):
            value = '@' + value
        return value.lower()