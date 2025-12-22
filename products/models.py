from django.db import models

# Create your models here.
from django.db import models
from shops.models import Shop

class Category(models.Model):
    """
    مدل دسته‌بندی محصولات
    """
    name = models.CharField(
        max_length=100,
        verbose_name='نام دسته‌بندی'
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name='شناسه در URL'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='توضیحات'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='تاریخ ایجاد'
    )
    
    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    """
    مدل محصول - هر محصول متعلق به یک فروشگاه است
    """
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='فروشگاه'
    )
    
    # اطلاعات اصلی محصول
    name = models.CharField(
        max_length=200,
        verbose_name='نام محصول'
    )
    
    description = models.TextField(
        verbose_name='توضیحات محصول'
    )
    
    price = models.DecimalField(
        max_digits=12,
        decimal_places=0,  # قیمت به ریال
        verbose_name='قیمت (ریال)'
    )
    
    # موجودی و وضعیت
    stock = models.PositiveIntegerField(
        default=0,
        verbose_name='موجودی'
    )
    
    is_available = models.BooleanField(
        default=True,
        verbose_name='موجود است'
    )
    
    # دسته‌بندی
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
        verbose_name='دسته‌بندی'
    )
    
    # ویژگی‌های محصول (برای فیلتر کردن)
    size = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='سایز'
    )
    
    color = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='رنگ'
    )
    
    brand = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='برند'
    )
    
    material = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='جنس'
    )
    
    # تصاویر محصول (ذخیره به صورت JSON)
    images = models.JSONField(
        default=list,
        verbose_name='تصاویر محصول'
    )
    
    # اطلاعات متا
    views = models.PositiveIntegerField(
        default=0,
        verbose_name='تعداد بازدید'
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
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shop', 'is_available']),
            models.Index(fields=['category']),
            models.Index(fields=['price']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.shop.shop_name}"
    
    def get_price_in_toman(self):
        """تبدیل قیمت از ریال به تومان"""
        return self.price / 10
    
    def is_in_stock(self):
        """بررسی موجودی محصول"""
        return self.stock > 0 and self.is_available
    
    def decrease_stock(self, quantity):
        """کاهش موجودی محصول پس از خرید"""
        if self.stock >= quantity:
            self.stock -= quantity
            if self.stock == 0:
                self.is_available = False
            self.save()
            return True
        return False