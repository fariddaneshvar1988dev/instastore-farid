from django.shortcuts import render

# Create your views here.
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Customer
from .serializers import CustomerSerializer, CustomerCreateSerializer
import random

class CustomerProfileAPIView(generics.RetrieveUpdateAPIView):
    """مشاهده و ویرایش پروفایل مشتری"""
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # فرض: کاربر با شماره تلفن احراز هویت شده
        phone = self.request.user.username  # اگر از JWT استفاده کنیم
        return Customer.objects.get(phone_number=phone)

class SendOTPAPIView(APIView):
    """ارسال کد OTP برای احراز هویت مشتری"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone = request.data.get('phone_number')
        
        if not phone:
            return Response(
                {'error': 'شماره تلفن الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # در اینجا باید با سرویس SMS ادغام شود
        # برای توسعه، کد OTP ساده تولید می‌کنیم
        otp = str(random.randint(1000, 9999))
        
        # ذخیره OTP در session یا cache
        request.session[f'otp_{phone}'] = otp
        request.session[f'otp_{phone}_expire'] = time.time() + 300  # 5 دقیقه
        
        # TODO: ارسال واقعی SMS
        # در حالت توسعه، کد را برمی‌گردانیم
        if settings.DEBUG:
            return Response({
                'message': 'کد OTP ارسال شد',
                'otp': otp,  # فقط در حالت توسعه
                'phone': phone
            })
        
        return Response({'message': 'کد OTP ارسال شد'})

class VerifyOTPAPIView(APIView):
    """تأیید کد OTP و ورود مشتری"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        phone = request.data.get('phone_number')
        otp = request.data.get('otp')
        
        if not phone or not otp:
            return Response(
                {'error': 'شماره تلفن و کد OTP الزامی است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # بررسی OTP از session
        saved_otp = request.session.get(f'otp_{phone}')
        expire_time = request.session.get(f'otp_{phone}_expire', 0)
        
        if not saved_otp or time.time() > expire_time:
            return Response(
                {'error': 'کد OTP منقضی شده یا وجود ندارد'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if saved_otp != otp:
            return Response(
                {'error': 'کد OTP نادرست است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # پیدا کردن یا ایجاد مشتری
        customer, created = Customer.objects.get_or_create(
            phone_number=phone
        )
        
        # تولید توکن JWT (اگر استفاده می‌کنید)
        # refresh = RefreshToken.for_user(customer)
        
        # پاک کردن OTP از session
        del request.session[f'otp_{phone}']
        del request.session[f'otp_{phone}_expire']
        
        return Response({
            'message': 'ورود موفقیت‌آمیز بود',
            'customer_id': str(customer.id),
            'phone_number': customer.phone_number,
            'is_new': created
            # 'refresh': str(refresh),
            # 'access': str(refresh.access_token),
        })