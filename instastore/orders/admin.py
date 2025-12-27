from django.contrib import admin
from .models import Order, OrderItem, CustomerCart

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    # فیلد product_price وجود ندارد، به جای آن از unit_price استفاده می‌کنیم
    readonly_fields = ('product_name', 'unit_price', 'total_price', 'variant', 'size', 'color')
    can_delete = False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'shop', 'customer_phone', 'status', 'total_amount', 'created_at')
    list_filter = ('status', 'created_at', 'shop')
    search_fields = ('order_id', 'customer_phone', 'customer_name')
    
    # فیلد delivered_at از مدل حذف شده بود، پس از اینجا هم حذفش می‌کنیم
    readonly_fields = ('created_at', 'updated_at')
    
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('اطلاعات سفارش', {
            'fields': ('order_id', 'shop', 'customer', 'status', 'created_at')
        }),
        ('اطلاعات مالی', {
            'fields': ('subtotal', 'shipping_cost', 'discount', 'total_amount', 'payment_method', 'payment_status')
        }),
        ('اطلاعات ارسال', {
            'fields': ('customer_name', 'customer_phone', 'shipping_address', 'tracking_code')
        }),
        ('یادداشت‌ها', {
            'fields': ('customer_notes', 'admin_notes')
        })
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    # اصلاح نام فیلدها طبق مدل جدید
    list_display = ('order', 'product_name', 'quantity', 'unit_price', 'total_price')
    list_filter = ('order__shop',)
    search_fields = ('order__order_id', 'product_name')
    readonly_fields = ('unit_price', 'total_price')

@admin.register(CustomerCart)
class CustomerCartAdmin(admin.ModelAdmin):
    list_display = ('customer', 'updated_at')