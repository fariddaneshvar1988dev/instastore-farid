from django.db import models
from django.conf import settings
from shops.models import Shop
from products.models import Product, ProductVariant

class Order(models.Model):
    # وضعیت‌های سفارش (Status Flow)
    STATUS_CHOICES = (
        ('pending', 'در انتظار پرداخت'),
        ('paid', 'پرداخت شده'),
        ('processing', 'در حال پردازش'),
        ('shipped', 'ارسال شده'),
        ('canceled', 'لغو شده'),
    )

    # 1. اتصال حیاتی به فروشگاه (برای اینکه بدانیم سفارش مالِ کدام پیج است)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='orders', verbose_name='فروشگاه')
    
    # 2. خریدار (می‌تواند کاربر لاگین شده باشد یا نال)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders', verbose_name='کاربر')
    
    # 3. اطلاعات ارسال (Snapshot)
    full_name = models.CharField(max_length=100, verbose_name='نام و نام خانوادگی گیرنده')
    phone_number = models.CharField(max_length=15, verbose_name='شماره تماس')
    address = models.TextField(verbose_name='آدرس کامل پستی')
    postal_code = models.CharField(max_length=20, verbose_name='کد پستی')
    
    # 4. اطلاعات مالی
    total_price = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='مبلغ کل (ریال)')
    is_paid = models.BooleanField(default=False, verbose_name='پرداخت شده؟')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='وضعیت')
    
    # 5. ردپای زمانی
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ثبت')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین تغییر')

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'سفارش'
        verbose_name_plural = 'سفارشات'

    def __str__(self):
        return f"Order {self.id} - {self.shop.name}"

    def get_total_cost(self):
        """جمع کل اقلام سفارش"""
        return sum(item.get_cost() for item in self.items.all())


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE, verbose_name='سفارش')
    
    # اتصال به محصول کلی (برای دسترسی به نام و عکس)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items', verbose_name='محصول')
    
    # اتصال حیاتی به تنوع محصول (برای مدیریت موجودی انبار)
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, related_name='order_items', verbose_name='تنوع انتخاب شده')
    
    # ذخیره قیمت در لحظه خرید (خیلی مهم: اگر فردا قیمت عوض شد، فاکتور قدیمی نباید عوض شود)
    price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت واحد در لحظه خرید')
    
    quantity = models.PositiveIntegerField(default=1, verbose_name='تعداد')

    class Meta:
        verbose_name = 'آیتم سفارش'
        verbose_name_plural = 'آیتم‌های سفارش'

    def __str__(self):
        return str(self.id)

    def get_cost(self):
        return self.price * self.quantity
    
    def save(self, *args, **kwargs):
        # اگر قیمت ست نشده بود، قیمت فعلی واریانت را بردار
        if not self.price and self.variant:
            self.price = self.variant.final_price
        super().save(*args, **kwargs)