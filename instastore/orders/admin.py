from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # فیلدها باید دقیقاً با models.py یکی باشند
    readonly_fields = ('product', 'variant', 'price', 'quantity')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # اصلاح نام فیلدها بر اساس فایل models.py شما
    list_display = ('id', 'shop', 'phone_number', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at', 'shop')
    search_fields = ('id', 'phone_number', 'full_name', 'address')
    
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('shop', 'user', 'status', 'created_at', 'updated_at')
        }),
        ('اطلاعات مالی', {
            'fields': ('total_price', 'is_paid')
        }),
        ('اطلاعات ارسال', {
            'fields': ('full_name', 'phone_number', 'postal_code', 'address')
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'product', 'quantity', 'price')
    list_filter = ('order__shop',)
    search_fields = ('order__id', 'product__name')
    readonly_fields = ('price',)