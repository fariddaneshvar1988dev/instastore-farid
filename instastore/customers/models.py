from django.db import models
from django.contrib.auth.models import User
from shops.models import Shop  # اضافه کردن import
import uuid

class Customer(models.Model):
    """
    مدل مشتری - هر مشتری متعلق به یک فروشگاه خاص است
    """
    # اتصال به فروشگاه (اضافه شده)
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='customers',
        verbose_name='فروشگاه',
        
    )
    
    # اتصال به یوزر جنگو (اختیاری)
    user = models.OneToOneField(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='customer_profile',
        verbose_name='کاربر مرتبط'
    )

    phone_number = models.CharField(
        max_length=15,
        verbose_name='شماره تلفن'
        # ❗️ unique=True حذف شد - در سطح shop بررسی می‌شود
    )
    
    # شناسه یکتا برای مشتری
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    full_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='نام کامل'
    )
    
    # آدرس مشتری
    default_address = models.TextField(
        blank=True,
        verbose_name='آدرس پیش‌فرض'
    )
    
    # تنظیمات و اطلاعات
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال'
    )
    
    # آمار و اطلاعات
    total_orders = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد سفارشات'
    )
    
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name='مجموع خریدها (ریال)'
    )
    
    # تاریخ‌ها
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    
    last_seen = models.DateTimeField(
        auto_now=True,
        verbose_name='آخرین بازدید'
    )
    
    class Meta:
        verbose_name = 'مشتری'
        verbose_name_plural = 'مشتریان'
        ordering = ['-created_at']
        # 🔥 مهم: شماره تلفن در هر فروشگاه یکتا باشد
        unique_together = ['shop', 'phone_number']
        indexes = [
            models.Index(fields=['shop', 'phone_number']),
            models.Index(fields=['shop', 'created_at']),
        ]
    
    def __str__(self):
        if self.full_name:
            return f"{self.full_name} ({self.phone_number}) - {self.shop.shop_name}"
        return f"{self.phone_number} ({self.shop.shop_name})"
    
    def update_stats(self, order_amount):
        """به‌روزرسانی آمار مشتری پس از سفارش جدید"""
        self.total_orders += 1
        self.total_spent += order_amount
        self.save()
    
    @classmethod
    def get_or_create_for_shop(cls, shop, phone_number, **extra_fields):
        """
        دریافت یا ایجاد مشتری برای یک فروشگاه خاص
        """
        try:
            customer = cls.objects.get(shop=shop, phone_number=phone_number)
            created = False
        except cls.DoesNotExist:
            customer = cls.objects.create(
                shop=shop,
                phone_number=phone_number,
                **extra_fields
            )
            created = True
        
        return customer, created