from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'full_name', 'shop', 'total_orders', 'total_spent', 'created_at')
    list_filter = ('shop', 'is_active', 'created_at')
    search_fields = ('phone_number', 'full_name', 'shop__shop_name')
    readonly_fields = ('id', 'created_at', 'last_seen', 'total_orders', 'total_spent')
    
    fieldsets = (
        ('اطلاعات مشتری', {
            'fields': ('shop', 'phone_number', 'full_name', 'default_address')
        }),
        ('اطلاعات کاربر', {
            'fields': ('user',)
        }),
        ('آمار و وضعیت', {
            'fields': ('is_active', 'total_orders', 'total_spent', 'last_seen')
        }),
        ('اطلاعات سیستمی', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        # فقط مشتریان فروشگاه‌های فعال را نشان بده
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(shop__is_active=True)