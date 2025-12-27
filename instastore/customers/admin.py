from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'full_name', 'total_orders', 'total_spent', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('phone_number', 'full_name')
    readonly_fields = ('total_orders', 'total_spent', 'created_at', 'last_seen')
    fieldsets = (
        ('اطلاعات مشتری', {
            'fields': ('phone_number', 'full_name', 'default_address')
        }),
        ('آمار خرید', {
            'fields': ('total_orders', 'total_spent')
        }),
        ('تنظیمات', {
            'fields': ('is_active',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'last_seen'),
            'classes': ('collapse',)
        }),
    )