from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Order
from .serializers import OrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت سفارشات.
    - ایجاد سفارش: برای همه آزاد است (مهمان و عضو).
    - مشاهده لیست: فقط برای کاربر احراز هویت شده.
    """
    serializer_class = OrderSerializer
    
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
        """متد ایجاد سفارش را بازنویسی می‌کنیم تا خروجی تمیزتری بدهد"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        headers = self.get_success_headers(serializer.data)
        response_data = {
            'status': 'success',
            'message': 'سفارش با موفقیت ثبت شد.',
            'order_id': order.order_id,
            'total_amount': order.total_amount
        }
        return Response(response_data, status=status.HTTP_201_CREATED, headers=headers)