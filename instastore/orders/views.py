# orders/views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum
from .models import Order
from .serializers import OrderSerializer, OrderStatusUpdateSerializer, AdminOrderSerializer

class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت سفارشات
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'is_paid', 'shop']
    search_fields = ['full_name', 'phone_number', 'postal_code', 'address', 'order_number']
    ordering_fields = ['created_at', 'total_price', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        user = self.request.user
        
        # ادمین همه سفارشات را می‌بیند
        if user.is_staff or user.is_superuser:
            return Order.objects.all()
        
        # صاحب فروشگاه سفارشات فروشگاه خود را می‌بیند
        if hasattr(user, 'shop'):
            return Order.objects.filter(shop__user=user)
        
        # کاربر عادی فقط سفارشات خود را می‌بیند
        return Order.objects.filter(user=user)
    
    def get_serializer_class(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return AdminOrderSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """
        آپدیت وضعیت سفارش
        """
        order = self.get_object()
        serializer = OrderStatusUpdateSerializer(order, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            
            # ثبت لاگ تغییر وضعیت
            from django.contrib.admin.models import LogEntry, CHANGE
            from django.contrib.contenttypes.models import ContentType
            
            LogEntry.objects.log_action(
                user_id=request.user.id,
                content_type_id=ContentType.objects.get_for_model(order).pk,
                object_id=order.id,
                object_repr=str(order),
                action_flag=CHANGE,
                change_message=f"تغییر وضعیت به: {serializer.validated_data['status']}"
            )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_as_paid(self, request, pk=None):
        """
        علامت‌گذاری سفارش به عنوان پرداخت شده
        """
        order = self.get_object()
        
        if order.is_paid:
            return Response(
                {'error': 'این سفارش قبلاً پرداخت شده است.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.is_paid = True
        order.status = 'paid'
        order.save()
        
        return Response({'status': 'پرداخت با موفقیت ثبت شد.'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        آمار سفارشات
        """
        queryset = self.get_queryset()
        
        stats = {
            'total_orders': queryset.count(),
            'pending_orders': queryset.filter(status='pending').count(),
            'paid_orders': queryset.filter(is_paid=True).count(),
            'total_revenue': queryset.filter(is_paid=True).aggregate(
                total=Sum('total_price')
            )['total'] or 0,
            'average_order_value': queryset.filter(is_paid=True).aggregate(
                avg=Sum('total_price') / Sum('items__quantity')
            )['avg'] or 0,
        }
        
        return Response(stats)

class ShopOrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet برای مشاهده سفارشات هر فروشگاه
    """
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at', 'total_price']
    ordering = ['-created_at']
    
    def get_queryset(self):
        shop_id = self.kwargs.get('shop_id')
        user = self.request.user
        
        # اگر ادمین است
        if user.is_staff or user.is_superuser:
            return Order.objects.filter(shop_id=shop_id)
        
        # اگر صاحب فروشگاه است
        if hasattr(user, 'shop'):
            return Order.objects.filter(
                shop_id=shop_id,
                shop__user=user
            )
        
        # اگر هیچکدام نیست، فقط سفارشات خودش را ببیند
        return Order.objects.filter(
            shop_id=shop_id,
            user=user
        )