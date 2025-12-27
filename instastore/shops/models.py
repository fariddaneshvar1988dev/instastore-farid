from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta

class Plan(models.Model):
    """
    مدل پلن‌های اشتراک (رایگان، ماهانه، سالانه و...)
    """
    PLAN_FREE = 'free'
    PLAN_BASIC = 'basic'
    PLAN_PRO = 'pro'
    
    CODE_CHOICES = [
        (PLAN_FREE, 'رایگان آزمایشی (۵ روز)'),
        (PLAN_BASIC, 'پایه – ماهانه'),
        (PLAN_PRO, 'حرفه‌ای – ماهانه'),
    ]

    code = models.CharField(max_length=20, choices=CODE_CHOICES, unique=True, verbose_name="کد سیستمی پلن")
    name = models.CharField(max_length=50, verbose_name="نام نمایشی")
    description = models.TextField(blank=True, verbose_name="توضیحات (برای نمایش در صفحه خرید)")
    price = models.PositiveIntegerField(default=0, verbose_name="قیمت (تومان)")
    
    # تنظیمات محدودیت‌ها
    days = models.PositiveSmallIntegerField(default=30, verbose_name="مدت اعتبار (روز)")
    max_products = models.PositiveSmallIntegerField(default=10, verbose_name="حداکثر تعداد محصول")
    max_orders_per_month = models.PositiveIntegerField(default=100, verbose_name="سقف سفارش ماهانه")
    
    is_active = models.BooleanField(default=True, verbose_name="قابل خرید")
    is_default = models.BooleanField(default=False, verbose_name="پلن پیش‌فرض ثبت‌نام")

    class Meta:
        verbose_name = "پلن اشتراک"
        verbose_name_plural = "پلن‌های اشتراک"
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.price} تومان"


class Shop(models.Model):
    """
    مدل اصلی فروشگاه
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop', verbose_name="صاحب فروشگاه")
    shop_name = models.CharField(max_length=200, verbose_name="نام فروشگاه")
    slug = models.SlugField(unique=True, blank=True, allow_unicode=True, verbose_name="شناسه در URL")
    
    # اطلاعات تماس و پروفایل
    instagram_username = models.CharField(max_length=100, unique=True, verbose_name="آیدی اینستاگرام")
    bio = models.TextField(blank=True, verbose_name="بیوگرافی کوتاه")
    phone_number = models.CharField(max_length=15, verbose_name="شماره تماس پشتیبانی")
    address = models.TextField(blank=True, verbose_name="آدرس فروشگاه (اختیاری)")
    logo = models.ImageField(upload_to='shop_logos/', blank=True, null=True, verbose_name="لوگو")
    
    is_active = models.BooleanField(default=True, verbose_name="وضعیت فروشگاه")

    # تنظیمات مالی و پرداخت
    enable_cod = models.BooleanField(default=True, verbose_name="پرداخت در محل")
    
    enable_card_to_card = models.BooleanField(default=False, verbose_name="کارت به کارت")
    card_owner_name = models.CharField(max_length=100, blank=True, verbose_name="نام صاحب کارت")
    card_number = models.CharField(max_length=16, blank=True, verbose_name="شماره کارت")
    shaba_number = models.CharField(max_length=26, blank=True, verbose_name="شماره شبا")
    
    enable_online_payment = models.BooleanField(default=False, verbose_name="پرداخت آنلاین (زرین‌پال)")
    zarinpal_merchant_id = models.CharField(max_length=36, blank=True, verbose_name="مرچنت کد زرین‌پال")

    # وضعیت اشتراک
    current_plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="پلن فعال")
    plan_started_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ شروع اشتراک")
    plan_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ انقضای اشتراک")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تاسیس")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")

    class Meta:
        verbose_name = "فروشگاه"
        verbose_name_plural = "فروشگاه‌ها"

    def save(self, *args, **kwargs):
        # 1. تولید Slug فقط برای بار اول (برای جلوگیری از تغییر لینک‌ها در آینده)
        if not self.slug:
            base_slug = slugify(self.instagram_username, allow_unicode=True)
            # اگر اسلاگ خالی بود (مثلا حروف فارسی خاص)، از آیدی یوزر استفاده کن
            if not base_slug:
                base_slug = f"shop-{self.user.id}"
            
            slug = base_slug
            counter = 1
            while Shop.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # 2. اختصاص پلن رایگان برای فروشگاه جدید
        if self._state.adding and not self.current_plan:
            # تلاش برای پیدا کردن پلن پیش‌فرض (که تیک is_default دارد)
            default_plan = Plan.objects.filter(is_default=True).first()
            
            # اگر پلن پیش‌فرضی نبود، دنبال پلن با کد 'free' بگرد
            if not default_plan:
                default_plan = Plan.objects.filter(code=Plan.PLAN_FREE).first()

            if default_plan:
                self.current_plan = default_plan
                self.plan_started_at = timezone.now()
                # تنظیم مدت زمان (مثلاً 5 روز)
                self.plan_expires_at = self.plan_started_at + timedelta(days=default_plan.days)

        super().save(*args, **kwargs)

    # ----------------------------------------
    # متدهای منطقی (Logic Methods)
    # ----------------------------------------

    def is_subscription_active(self):
        """آیا اشتراک فروشگاه معتبر است؟"""
        if not self.is_active:
            return False
        if not self.current_plan or not self.plan_expires_at:
            return False
        return timezone.now() < self.plan_expires_at

    @property
    def remaining_days(self):
        """تعداد روزهای باقی‌مانده از اشتراک"""
        if self.plan_expires_at:
            delta = self.plan_expires_at - timezone.now()
            return max(delta.days, 0)
        return 0

    def can_add_product(self):
        """آیا مجاز به افزودن محصول جدید است؟"""
        if not self.is_subscription_active():
            return False
        
        # استفاده از related_name='products' که در مدل Product تعریف شده
        current_count = self.products.filter(is_active=True).count()
        return current_count < self.current_plan.max_products

    def can_accept_order(self):
        """آیا سقف سفارش ماهانه پر نشده است؟"""
        if not self.is_subscription_active():
            return False
        
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        # استفاده از related_name='orders' که در مدل Order تعریف شده
        order_count = self.orders.filter(created_at__gte=current_month_start).count()
        
        return order_count < self.current_plan.max_orders_per_month

    def renew_subscription(self, new_plan):
        """
        تمدید یا ارتقای اشتراک
        این متد باید بعد از پرداخت موفق صدا زده شود.
        """
        now = timezone.now()
        
        # اگر اشتراک قبلی هنوز وقت دارد و همان پلن را تمدید کرده، به انتهای زمان فعلی اضافه کن
        if self.current_plan == new_plan and self.plan_expires_at and self.plan_expires_at > now:
            start_point = self.plan_expires_at
        else:
            # اگر پلن عوض شده یا اشتراک تمام شده، از الان حساب کن
            start_point = now
            
        self.current_plan = new_plan
        self.plan_started_at = now  # تاریخ آخرین پرداخت
        self.plan_expires_at = start_point + timedelta(days=new_plan.days)
        self.save()

    def __str__(self):
        return f"{self.shop_name} (@{self.instagram_username})"