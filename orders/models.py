from django.db import models
import uuid
import random
from datetime import datetime
from shops.models import Shop
from customers.models import Customer
# ایمپورت مدل جدید ProductVariant
from products.models import Product, ProductVariant

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'در انتظار تأیید'),
        ('confirmed', 'تأیید شده'),
        ('processing', 'در حال آماده‌سازی'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('cancelled', 'لغو شده'),
        ('refunded', 'عودت داده شده'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('cash_on_delivery', 'پرداخت در محل'),
        ('online', 'پرداخت آنلاین'),
        ('bank_transfer', 'کارت به کارت'),
    ]
    
    order_id = models.CharField(max_length=20, unique=True, editable=False, verbose_name='شماره سفارش')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders', verbose_name='فروشگاه')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True ,blank=True ,related_name='orders', verbose_name='مشتری')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash_on_delivery', verbose_name='روش پرداخت')
    payment_status = models.BooleanField(default=False, verbose_name='وضعیت پرداخت')
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مجموع اقلام')
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='هزینه ارسال')
    discount = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='تخفیف')
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ کل')
    
    # اطلاعات ارسال
    customer_phone = models.CharField(max_length=15, verbose_name='شماره تماس مشتری')
    customer_name = models.CharField(max_length=200, blank=True, verbose_name='نام مشتری')
    shipping_address = models.TextField(verbose_name='آدرس ارسال')
    customer_notes = models.TextField(blank=True, verbose_name='یادداشت مشتری')
    admin_notes = models.TextField(blank=True, verbose_name='یادداشت مدیریت')
    
    tracking_code = models.CharField(max_length=100, blank=True, verbose_name='کد رهگیری پستی')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    
    class Meta:
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.order_id}"
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            date_str = datetime.now().strftime('%y%m')
            while True:
                random_str = str(random.randint(100000, 999999))
                new_id = f"ORD{date_str}{random_str}"
                if not Order.objects.filter(order_id=new_id).exists():
                    self.order_id = new_id
                    break
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """محاسبه مجدد قیمت کل سفارش بر اساس آیتم‌ها"""
        self.subtotal = sum(item.total_price for item in self.items.all())
        self.total_amount = self.subtotal + self.shipping_cost - self.discount
        self.save()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='سفارش')
    
    # تغییر اصلی: اتصال به واریانت به جای محصول کلی
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT, related_name='order_items', verbose_name='محصول انتخابی')
    
    # ذخیره اطلاعات در لحظه خرید (Snapshot) تا تغییرات بعدی محصول روی فاکتور قبلی اثر نگذارد
    product_name = models.CharField(max_length=200, verbose_name='نام محصول')
    size = models.CharField(max_length=50, verbose_name='سایز')
    color = models.CharField(max_length=50, verbose_name='رنگ')
    
    unit_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت واحد')
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')
    total_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت کل')
    
    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'
    
    def __str__(self):
        return f"{self.product_name} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # پر کردن خودکار اطلاعات از روی واریانت
        if not self.product_name:
            self.product_name = self.variant.product.name
        if not self.size:
            self.size = self.variant.size
        if not self.color:
            self.color = self.variant.color
        if not self.unit_price:
            self.unit_price = self.variant.final_price
            
        self.total_price = self.unit_price * self.quantity
        
        super().save(*args, **kwargs)
        
        # کسر موجودی از واریانت مربوطه
        if is_new and self.order.status in ['pending', 'confirmed']:
            success = self.variant.decrease_stock(self.quantity)
            if not success:
                # اینجا می‌توانید منطق خطا را پیاده کنید، مثلاً پرتاب ارور اگر موجودی نبود
                pass

class CustomerCart(models.Model):
    """
    سبد خرید ساده برای نگهداری موقت آیتم‌ها قبل از تبدیل به سفارش
    """
    customer = models.OneToOneField('customers.Customer', on_delete=models.CASCADE, related_name='cart')
    # ساختار پیشنهادی برای JSON:
    # [{'variant_id': 1, 'quantity': 2, 'price': 100000}, ...]
    items = models.JSONField(default=list, verbose_name='آیتم‌های سبد')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)