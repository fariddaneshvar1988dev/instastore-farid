from django.db import models

# Create your models here.
from django.db import models
import uuid
from shops.models import Shop
from customers.models import Customer
from products.models import Product

class Order(models.Model):
    """
    مدل سفارش - هر سفارش متعلق به یک مشتری و یک فروشگاه است
    """
    # وضعیت‌های سفارش
    STATUS_CHOICES = [
        ('pending', 'در انتظار تأیید'),
        ('confirmed', 'تأیید شده'),
        ('processing', 'در حال آماده‌سازی'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'عودت داده شده'),
    ]
    
    # روش‌های پرداخت
    PAYMENT_METHOD_CHOICES = [
        ('cash_on_delivery', 'پرداخت در محل'),
        ('online', 'پرداخت آنلاین'),
        ('bank_transfer', 'کارت به کارت'),
    ]
    
    # شناسه سفارش (برای نمایش به مشتری)
    order_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        verbose_name='شماره سفارش'
    )
    
    # ارتباط با فروشگاه و مشتری
    shop = models.ForeignKey(
        Shop,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='فروشگاه'
    )
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='مشتری'
    )
    
    # وضعیت سفارش
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='وضعیت'
    )
    
    # اطلاعات پرداخت
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        default='cash_on_delivery',
        verbose_name='روش پرداخت'
    )
    
    payment_status = models.BooleanField(
        default=False,
        verbose_name='وضعیت پرداخت'
    )
    
    # اطلاعات مالی
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name='مجموع قیمت محصولات (ریال)'
    )
    
    shipping_cost = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name='هزینه ارسال (ریال)'
    )
    
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0,
        verbose_name='تخفیف (ریال)'
    )
    
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name='مبلغ کل (ریال)'
    )
    
    # اطلاعات مشتری در زمان سفارش
    customer_phone = models.CharField(
        max_length=15,
        verbose_name='شماره تماس مشتری'
    )
    
    customer_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='نام مشتری'
    )
    
    shipping_address = models.TextField(
        verbose_name='آدرس ارسال'
    )
    
    # توضیحات و یادداشت
    customer_notes = models.TextField(
        blank=True,
        verbose_name='یادداشت مشتری'
    )
    
    admin_notes = models.TextField(
        blank=True,
        verbose_name='یادداشت مدیریت'
    )
    
    # اطلاعات تحویل
    tracking_code = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='کد رهگیری پستی'
    )
    
    estimated_delivery = models.DateField(
        null=True,
        blank=True,
        verbose_name='تاریخ تحویل تخمینی'
    )
    
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='تاریخ تحویل'
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
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shop', 'status']),
            models.Index(fields=['order_id']),
            models.Index(fields=['customer']),
        ]
    
    def __str__(self):
        return f"سفارش #{self.order_id} - {self.shop.shop_name}"
    
    def save(self, *args, **kwargs):
        """ایجاد شماره سفارش یکتا"""
        if not self.order_id:
            # تولید شماره سفارش: ORD + سال + ماه + ۶ رقم تصادفی
            import random
            from datetime import datetime
            date_str = datetime.now().strftime('%y%m')
            random_str = str(random.randint(100000, 999999))
            self.order_id = f"ORD{date_str}{random_str}"
        
        # ذخیره اطلاعات مشتری از مدل Customer
        if not self.customer_phone:
            self.customer_phone = self.customer.phone_number
        if not self.customer_name and self.customer.full_name:
            self.customer_name = self.customer.full_name
        
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """محاسبه مجدد مجموع سفارش"""
        subtotal = sum(item.total_price for item in self.items.all())
        self.subtotal = subtotal
        self.total_amount = subtotal + self.shipping_cost - self.discount
        self.save()
    
    def can_be_cancelled(self):
        """بررسی امکان لغو سفارش"""
        return self.status in ['pending', 'confirmed']
    
    def get_status_display_fa(self):
        """نمایش وضعیت به فارسی"""
        status_dict = dict(self.STATUS_CHOICES)
        return status_dict.get(self.status, self.status)

class OrderItem(models.Model):
    """
    مدل آیتم‌های سفارش - هر آیتم یک محصول در سفارش
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='سفارش'
    )
    
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='order_items',
        verbose_name='محصول'
    )
    
    # اطلاعات محصول در زمان خرید
    product_name = models.CharField(
        max_length=200,
        verbose_name='نام محصول'
    )
    
    product_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        verbose_name='قیمت واحد در زمان خرید (ریال)'
    )
    
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name='تعداد'
    )
    
    # قیمت کل برای این آیتم
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        editable=False,
        verbose_name='قیمت کل (ریال)'
    )
    
    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'
    
    def __str__(self):
        return f"{self.product_name} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        """محاسبه قیمت کل و ذخیره اطلاعات محصول"""
        # ذخیره اطلاعات محصول
        if not self.product_name:
            self.product_name = self.product.name
        if not self.product_price:
            self.product_price = self.product.price
        
        # محاسبه قیمت کل
        self.total_price = self.product_price * self.quantity
        
        super().save(*args, **kwargs)
        
        # به‌روزرسانی موجودی محصول
        if self.order.status in ['pending', 'confirmed']:
            self.product.decrease_stock(self.quantity)




class CustomerCart(models.Model):
    """سبد خرید برای مشتریان ثبت‌نام‌کرده"""
    customer = models.OneToOneField(
        'customers.Customer',
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='مشتری'
    )
    
    items = models.JSONField(
        default=list,
        verbose_name='آیتم‌های سبد خرید'
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
        verbose_name = 'سبد خرید مشتری'
        verbose_name_plural = 'سبدهای خرید مشتریان'
    
    def __str__(self):
        return f"سبد خرید {self.customer.phone_number}"
