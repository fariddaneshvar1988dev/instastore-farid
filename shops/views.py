# در shops/views.py اضافه کنید (در انتهای فایل)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.utils.text import slugify
from .models import Shop
import re

class RegisterSellerAPIView(APIView):
    """API برای ثبت‌نام صاحب پیج جدید"""
    def post(self, request):
        data = request.data
        
        # اعتبارسنجی ساده
        errors = {}
        
        # بررسی username
        if User.objects.filter(username=data.get('username')).exists():
            errors['username'] = 'این نام کاربری قبلاً استفاده شده است'
        
        # بررسی instagram username
        insta_user = data.get('instagram_username', '')
        if insta_user.startswith('@'):
            insta_user = insta_user[1:]
        
        if Shop.objects.filter(instagram_username=f'@{insta_user}').exists():
            errors['instagram_username'] = 'این پیج اینستاگرام قبلاً ثبت شده است'
        
        # بررسی شماره تلفن
        phone = data.get('phone_number', '')
        if not re.match(r'^09\d{9}$', phone):
            errors['phone_number'] = 'شماره تلفن معتبر نیست'
        
        if errors:
            return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # ایجاد کاربر
            user = User.objects.create_user(
                username=data['username'],
                email=data.get('email', ''),
                password=data['password'],
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', '')
            )
            
            # ایجاد فروشگاه
            shop = Shop.objects.create(
                user=user,
                instagram_username=f'@{insta_user}',
                shop_name=data['shop_name'],
                phone_number=phone,
                email=data.get('email', ''),
                bio=data.get('bio', ''),
                address=data.get('address', ''),
                slug=slugify(insta_user)
            )
            
            return Response({
                'message': 'ثبت‌نام موفقیت‌آمیز بود!',
                'shop': {
                    'id': shop.id,
                    'name': shop.shop_name,
                    'instagram': shop.instagram_username,
                    'slug': shop.slug,
                    'shop_url': f"http://127.0.0.1:8000/shop/{shop.slug}/"
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )