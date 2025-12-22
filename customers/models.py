from django.db import models

# Create your models here.
from django.db import models
import uuid

class Customer(models.Model):
    """
    مدل مشتری - نیازی به ثبت‌نام دارد، فقط شماره تلفن کافیست
    """
    # شناسه یکتا برای مشتری
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # اطلاعات مشتری
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        verbose_name='شماره تلفن'
    )
    
    full_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='نام کامل'
    )
    
    # آدرس مشتری (می‌تواند چند آدرس داشته باشد)
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
    
    def __str__(self):
        if self.full_name:
            return f"{self.full_name} ({self.phone_number})"
        return self.phone_number
    
    def update_stats(self, order_amount):
        """به‌روزرسانی آمار مشتری پس از سفارش جدید"""
        self.total_orders += 1
        self.total_spent += order_amount
        self.save()