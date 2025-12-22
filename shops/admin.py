from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Shop

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """تنظیمات نمایش فروشگاه در پنل ادمین"""
    list_display = ('shop_name', 'instagram_username', 'user', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('shop_name', 'instagram_username', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('user', 'shop_name', 'instagram_username', 'slug', 'bio')
        }),
        ('اطلاعات تماس', {
            'fields': ('phone_number', 'email', 'address')
        }),
        ('تنظیمات', {
            'fields': ('is_active',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )