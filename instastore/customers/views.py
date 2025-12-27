from django.shortcuts import render
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings  # مهم: ایمپورت تنظیمات
from .models import Customer
from .serializers import CustomerSerializer
import random
import time  # مهم: ایمپورت زمان

class CustomerProfileAPIView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        phone = self.request.user.username
        return Customer.objects.get(phone_number=phone)

class SendOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone = request.data.get('phone_number')
        if not phone:
            return Response({'error': 'شماره تلفن الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp = str(random.randint(1000, 9999))
        request.session[f'otp_{phone}'] = otp
        request.session[f'otp_{phone}_expire'] = time.time() + 300
        
        if settings.DEBUG:
            return Response({'message': 'کد OTP ارسال شد', 'otp': otp, 'phone': phone})
        return Response({'message': 'کد OTP ارسال شد'})

class VerifyOTPAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone = request.data.get('phone_number')
        otp = request.data.get('otp')
        
        if not phone or not otp:
            return Response({'error': 'شماره تلفن و کد OTP الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        saved_otp = request.session.get(f'otp_{phone}')
        expire_time = request.session.get(f'otp_{phone}_expire', 0)
        
        if not saved_otp or time.time() > expire_time:
            return Response({'error': 'کد OTP منقضی شده یا وجود ندارد'}, status=status.HTTP_400_BAD_REQUEST)
        
        if saved_otp != otp:
            return Response({'error': 'کد OTP نادرست است'}, status=status.HTTP_400_BAD_REQUEST)
        
        customer, created = Customer.objects.get_or_create(phone_number=phone)
        
        # پاک کردن سشن
        request.session.pop(f'otp_{phone}', None)
        request.session.pop(f'otp_{phone}_expire', None)
        
        return Response({
            'message': 'ورود موفقیت‌آمیز بود',
            'customer_id': str(customer.id),
            'phone_number': customer.phone_number,
            'is_new': created
        })