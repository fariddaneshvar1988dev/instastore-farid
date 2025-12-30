from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Order
from .serializers import OrderSerializer
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return 

class OrderViewSet(viewsets.ModelViewSet):
    """مدیریت سفارشات از طریق API"""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    # استفاده از UnsafeSessionAuthentication برای جلوگیری از خطای CSRF در API
    authentication_classes = [UnsafeSessionAuthentication, BasicAuthentication]
    
    def get_queryset(self):
        """کاربر فقط سفارشات خودش را ببیند"""
        user = self.request.user
        if user.is_staff:
            return Order.objects.all()
        if user.is_authenticated and hasattr(user, 'customer_profile'):
            return Order.objects.filter(customer__user=user)
        return Order.objects.none()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        """متد ایجاد سفارش با مدیریت دقیق خطاها"""
        serializer = self.get_serializer(data=request.data)
        
        # ۱. بررسی اعتبارسنجی داده‌ها
        if not serializer.is_valid():
            # چاپ خطا در کنسول برای دیباگ
            print("❌ Order Validation Errors:", serializer.errors)
            # بازگرداندن متن خطا به فرانت‌اند
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            # ۲. تلاش برای ذخیره سفارش
            order = serializer.save()
            
            headers = self.get_success_headers(serializer.data)
            response_data = {
                'status': 'success',
                'message': 'سفارش با موفقیت ثبت شد.',
                'order_id': order.order_id,
                'total_amount': order.total_amount
            }
            return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)
            
        except Exception as e:
            # ۳. مدیریت خطاهای غیرمنتظره (مثل خطای دیتابیس)
            print("❌ Order Creation Error:", str(e))
            return Response(
                {'error': f'خطا در ثبت سفارش: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )