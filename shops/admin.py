from django.contrib import admin
from .models import Plan, Shop

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'price', 'days', 'max_products', 'max_orders_per_month', 'is_active')
    list_filter = ('is_active', 'price')
    search_fields = ('name', 'code')
    ordering = ('price',)

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = (
        'shop_name', 'instagram_username', 'user', 'current_plan', 'plan_expires_at',
        'remaining_days_display', 'subscription_status_display', 'is_active', 'created_at'
    )
    list_filter = ('is_active', 'current_plan', 'created_at')
    search_fields = ('shop_name', 'instagram_username', 'user__username')
    readonly_fields = ('slug', 'created_at', 'plan_started_at', 'plan_expires_at')
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': ('user', 'shop_name', 'slug', 'instagram_username', 'bio', 'phone_number', 'address', 'is_active')
        }),
        ('تنظیمات پرداخت', {
            'fields': (
                'enable_cod', 'enable_card_to_card', 'card_owner_name', 'card_number',
                'shaba_number', 'enable_online_payment', 'zarinpal_merchant_id'
            )
        }),
        ('اشتراک', {
            'fields': ('current_plan', 'plan_started_at', 'plan_expires_at')
        }),
    )

    # نام توابع را تغییر دادم تا با نام فیلدهای مدل تداخل نداشته باشد
    def remaining_days_display(self, obj):
        # اصلاح مهم: حذف پرانتز ()
        return obj.remaining_days
    remaining_days_display.short_description = "روز باقی‌مانده"

    def subscription_status_display(self, obj):
        # اصلاح: is_subscription_active یک متد معمولی است یا پراپرتی؟
        # طبق کدهای قبلی، این یک متد معمولی بود، پس پرانتز می‌خواهد.
        # اما اگر آن را هم @property کرده‌اید، پرانتز را بردارید.
        # فرض بر متد بودن (طبق فایل models.py قبلی):
        return obj.is_subscription_active()
    subscription_status_display.boolean = True
    subscription_status_display.short_description = "اشتراک فعال؟"