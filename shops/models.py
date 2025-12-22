from django.db import models

# Create your models here.
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
    
    # اطلاعات فروشگاه
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
    
    # آدرس فروشگاه
    address = models.TextField(
        blank=True,
        verbose_name='آدرس'
    )
    
    # تنظیمات فروشگاه
    is_active = models.BooleanField(
        default=True,
        verbose_name='فعال'
    )
    
    # تاریخ‌ها
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
        """اگر slug وجود نداشت، از instagram_username ساخته می‌شود"""
        if not self.slug:
            # ایجاد slug از نام کاربری اینستاگرام
            self.slug = slugify(self.instagram_username)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        """آدرس مطلق فروشگاه"""
        return f"/shop/{self.slug}/"