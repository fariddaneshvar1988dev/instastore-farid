from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

class Shop(models.Model):
    """
    مدل فروشگاه (Shop) - هر نمونه یک فروشگاه اینستاگرامی است
    هر کاربر می‌تواند یک فروشگاه داشته باشد
    """
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE,
        related_name='shop',
        verbose_name='کاربر'
    )
    
    # === اطلاعات عمومی فروشگاه ===
    instagram_username = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='نام کاربری اینستاگرام'
    )
    
    shop_name = models.CharField(
        max_length=200,
        verbose_name='نام فروشگاه'
    )
    
    slug = models.SlugField(
        max_length=200,
        unique=True,
        blank=True,
        verbose_name='شناسه فروشگاه در URL'
    )
    
    bio = models.TextField(
        blank=True,
        verbose_name='درباره فروشگاه'
    )
    
    phone_number = models.CharField(
        max_length=15,
        verbose_name='شماره تماس'
    )
    
    email = models.EmailField(
        blank=True,
        verbose_name='ایمیل'
    )
    
    address = models.TextField(
        blank=True,
        verbose_name='آدرس'
    )
    
    # === تنظیمات پرداخت (بخش جدید) ===
    
    # 1. پرداخت در محل
    enable_cod = models.BooleanField(
        default=True, 
        verbose_name="فعالسازی پرداخت در محل"
    )

    # 2. کارت به کارت
    enable_card_to_card = models.BooleanField(
        default=False, 
        verbose_name="فعالسازی کارت به کارت"
    )
    card_owner_name = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="نام صاحب کارت"
    )
    card_number = models.CharField(
        max_length=16, 
        blank=True, 
        verbose_name="شماره کارت"
    )
    shaba_number = models.CharField(
        max_length=26, 
        blank=True, 
        verbose_name="شماره شبا (اختیاری)"
    )

    # 3. درگاه پرداخت (مثل زرین‌پال)
    enable_online_payment = models.BooleanField(
        default=False, 
        verbose_name="فعالسازی درگاه آنلاین"
    )
    zarinpal_merchant_id = models.CharField(
        max_length=36, 
        blank=True, 
        verbose_name="مرچنت کد زرین‌پال"
    )
    
    # === وضعیت و تاریخ‌ها ===
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='آخرین بروزرسانی'
    )
    
    class Meta:
        verbose_name = 'فروشگاه'
        verbose_name_plural = 'فروشگاه‌ها'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.shop_name} (@{self.instagram_username})"
    
    def save(self, *args, **kwargs):
        # اگر اسلاگ خالی بود، از روی نام فروشگاه بساز
        if not self.slug:
            self.slug = slugify(self.shop_name, allow_unicode=True)
        super().save(*args, **kwargs)