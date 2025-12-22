from django.contrib import admin
from .models import Order, OrderItem
from django.utils import timezone

class OrderItemInline(admin.TabularInline):
    """نمایش آیتم‌های سفارش به صورت inline"""
    model = OrderItem
    extra = 0
    readonly_fields = ('product_name', 'product_price', 'total_price')
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_id', 
        'shop', 
        'customer_name', 
        'total_amount', 
        'status', 
        'payment_status',  # اضافه کردن این خط
        'created_at'
    )
    list_filter = ('status', 'payment_method', 'payment_status', 'created_at')
    search_fields = ('order_id', 'customer_phone', 'customer_name', 'shop__shop_name')
    readonly_fields = ('order_id', 'created_at', 'updated_at', 'delivered_at')
    list_editable = ('status', 'payment_status')  # اینجا حالا درست است
    inlines = [OrderItemInline]
    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('order_id', 'shop', 'customer', 'status')
        }),
        ('اطلاعات پرداخت', {
            'fields': ('payment_method', 'payment_status')
        }),
        ('اطلاعات مالی', {
            'fields': ('subtotal', 'shipping_cost', 'discount', 'total_amount')
        }),
        ('اطلاعات مشتری', {
            'fields': ('customer_phone', 'customer_name', 'shipping_address')
        }),
        ('اطلاعات تحویل', {
            'fields': ('tracking_code', 'estimated_delivery', 'delivered_at'),
            'classes': ('collapse',)
        }),
        ('یادداشت‌ها', {
            'fields': ('customer_notes', 'admin_notes'),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_shipped', 'mark_as_delivered']
    
    def mark_as_shipped(self, request, queryset):
        """اکشن برای علامت‌گذاری به عنوان ارسال شده"""
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} سفارش به حالت ارسال شده تغییر یافت.')
    mark_as_shipped.short_description = 'علامت‌گذاری به عنوان ارسال شده'
    
    def mark_as_delivered(self, request, queryset):
        """اکشن برای علامت‌گذاری به عنوان تحویل داده شده"""
        updated = queryset.update(status='delivered', delivered_at=timezone.now())
        self.message_user(request, f'{updated} سفارش به حالت تحویل داده شده تغییر یافت.')
    mark_as_delivered.short_description = 'علامت‌گذاری به عنوان تحویل داده شده'

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'order', 'quantity', 'product_price', 'total_price')
    list_filter = ('order__shop',)
    search_fields = ('product_name', 'order__order_id')
    readonly_fields = ('product_name', 'product_price', 'total_price')