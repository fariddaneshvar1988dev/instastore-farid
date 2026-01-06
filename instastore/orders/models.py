# orders/models.py
from django.db import models
from django.conf import settings
from django.db.models import Sum
from shops.models import Shop
from products.models import Product, ProductVariant

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('delivered', 'تحویل داده شده'),
        ('canceled', 'لغو شده'),
        ('refunded', 'مرجوع شده'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('online', 'پرداخت آنلاین'),
        ('cash', 'پرداخت در محل'),
        ('bank', 'کارت به کارت'),
    )
    
    # اتصال به فروشگاه
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders', verbose_name='فروشگاه')
    
    # خریدار
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                            null=True, blank=True, related_name='orders', verbose_name='کاربر')
    
    # اطلاعات ارسال
    full_name = models.CharField(max_length=100, verbose_name='نام و نام خانوادگی گیرنده')
    phone_number = models.CharField(max_length=15, verbose_name='شماره تماس')
    address = models.TextField(verbose_name='آدرس کامل پستی')
    postal_code = models.CharField(max_length=20, verbose_name='کد پستی')
    city = models.CharField(max_length=50, default='', verbose_name='شهر')
    province = models.CharField(max_length=50, default='', verbose_name='استان')
    
    # اطلاعات سفارش
    order_number = models.CharField(max_length=20, unique=True, blank=True, verbose_name='شماره سفارش')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, 
                                     default='online', verbose_name='روش پرداخت')
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده؟')
    total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ کل (ریال)')
    
    # اطلاعات ارسال
    shipping_method = models.CharField(max_length=50, default='پست پیشتاز', verbose_name='روش ارسال')
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=0, default=0, verbose_name='هزینه ارسال')
    tracking_code = models.CharField(max_length=100, blank=True, verbose_name='کد رهگیری')
    
    # توضیحات
    notes = models.TextField(blank=True, verbose_name='توضیحات')
    
    # ردپای زمانی
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین تغییر')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ پرداخت')
    shipped_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ ارسال')
    delivered_at = models.DateTimeField(null=True, blank=True, verbose_name='تاریخ تحویل')

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return f"سفارش {self.order_number or self.id} - {self.shop.name}"

    def save(self, *args, **kwargs):
        # ایجاد شماره سفارش منحصر به فرد
        if not self.order_number:
            import datetime
            prefix = 'ORD'
            date_str = datetime.datetime.now().strftime('%y%m%d')
            last_order = Order.objects.filter(order_number__startswith=f'{prefix}{date_str}').count()
            self.order_number = f'{prefix}{date_str}{str(last_order + 1).zfill(4)}'
        
        # تاریخ پرداخت
        if self.is_paid and not self.paid_at:
            from django.utils import timezone
            self.paid_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        """محاسبه قیمت کل سفارش"""
        items_total = sum(item.get_cost() for item in self.items.all())
        self.total_price = items_total + self.shipping_cost
        self.save(update_fields=['total_price'])
        return self.total_price
    
    def get_status_display_fa(self):
        """نمایش فارسی وضعیت"""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)
    
    def get_payment_method_display_fa(self):
        """نمایش فارسی روش پرداخت"""
        return dict(self.PAYMENT_METHOD_CHOICES).get(self.payment_method, self.payment_method)
    
    def can_be_canceled(self):
        """بررسی امکان لغو سفارش"""
        return self.status in ['pending', 'paid', 'processing']
    
    @property
    def item_count(self):
        """تعداد اقلام در سفارش"""
        return self.items.count()
    
    @property
    def total_quantity(self):
        """تعداد کل آیتم‌ها (مجموع quantity)"""
        return self.items.aggregate(total=Sum('quantity'))['total'] or 0


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='سفارش')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items', verbose_name='محصول')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, 
                               related_name='order_items', verbose_name='تنوع انتخاب شده')
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت واحد در لحظه خرید')
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')
    
    # اطلاعات اضافی برای نمایش
    product_name = models.CharField(max_length=200, blank=True, verbose_name='نام محصول')
    variant_info = models.CharField(max_length=200, blank=True, verbose_name='اطلاعات تنوع')
    product_image = models.ImageField(upload_to='order_items/', null=True, blank=True, verbose_name='عکس محصول')

    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'
        indexes = [
            models.Index(fields=['order']),
            models.Index(fields=['product']),
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product_name or self.product.name}"

    def save(self, *args, **kwargs):
        # ذخیره اطلاعات محصول برای نمایش
        if not self.product_name and self.product:
            self.product_name = self.product.name
        
        if not self.variant_info and self.variant:
            self.variant_info = str(self.variant)
        
        # ذخیره قیمت اگر ست نشده
        if not self.price and self.variant:
            self.price = self.variant.final_price
        
        # ذخیره عکس محصول
        if not self.product_image and self.product.images.exists():
            self.product_image = self.product.images.first().image
        
        super().save(*args, **kwargs)
    
    def get_cost(self):
        """محاسبه هزینه کل این آیتم"""
        return self.price * self.quantity
    
    @property
    def unit_price_display(self):
        """قیمت واحد به صورت فرمت شده"""
        return f"{self.price:,} ریال"
    
    @property
    def total_price_display(self):
        """قیمت کل به صورت فرمت شده"""
        return f"{self.get_cost():,} ریال"