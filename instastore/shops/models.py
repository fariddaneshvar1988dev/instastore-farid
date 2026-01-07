from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Sum, F, ExpressionWrapper, DurationField
from datetime import timedelta
import uuid

class Plan(models.Model):
    """
    مدل پلن‌های اشتراک (رایگان، ماهانه، سالانه و...)
    """
    PLAN_FREE = 'free'
    PLAN_BASIC = 'basic'
    PLAN_PRO = 'pro'
    PLAN_ENTERPRISE = 'enterprise'
    
    CODE_CHOICES = [
        (PLAN_FREE, 'رایگان آزمایشی (۵ روز)'),
        (PLAN_BASIC, 'پایه – ماهانه'),
        (PLAN_PRO, 'حرفه‌ای – ماهانه'),
        (PLAN_ENTERPRISE, 'سازمانی – سالانه'),
    ]

    code = models.CharField(max_length=20, choices=CODE_CHOICES, unique=True, verbose_name="کد سیستمی پلن")
    name = models.CharField(max_length=50, verbose_name="نام نمایشی")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    price = models.PositiveIntegerField(default=0, verbose_name="قیمت (تومان)")
    
    # تنظیمات محدودیت‌ها
    days = models.PositiveSmallIntegerField(default=30, verbose_name="مدت اعتبار (روز)")
    max_products = models.PositiveSmallIntegerField(default=10, verbose_name="حداکثر تعداد محصول")
    max_orders_per_month = models.PositiveIntegerField(default=100, verbose_name="سقف سفارش ماهانه")
    
    # تنظیمات نمایش
    is_active = models.BooleanField(default=True, verbose_name="قابل خرید")
    is_default = models.BooleanField(default=False, verbose_name="پلن پیش‌فرض ثبت‌نام")
    is_popular = models.BooleanField(default=False, verbose_name="پلن پرطرفدار")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="ترتیب نمایش")

    class Meta:
        verbose_name = "پلن اشتراک"
        verbose_name_plural = "پلن‌های اشتراک"
        ordering = ['sort_order', 'price']
        indexes = [
            models.Index(fields=['code', 'is_active']),
            models.Index(fields=['price', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.price:,} تومان"

    def clean(self):
        """اعتبارسنجی پلن"""
        super().clean()
        
        if self.days <= 0:
            raise ValidationError({'days': 'مدت اعتبار باید بیشتر از صفر باشد'})
        
        if self.code == self.PLAN_FREE and self.price > 0:
            raise ValidationError({'price': 'پلن رایگان باید قیمت صفر داشته باشد'})

    def get_display_days(self):
        """نمایش مدت زمان به صورت خوانا"""
        if self.days == 5:
            return "۵ روز آزمایشی"
        elif self.days == 30:
            return "۱ ماه"
        elif self.days == 365:
            return "۱ سال"
        return f"{self.days} روز"


class ShopQuerySet(models.QuerySet):
    """QuerySet سفارشی برای Shop"""
    
    def with_subscription_info(self):
        """دریافت اطلاعات اشتراک"""
        return self.select_related(
            'current_plan', 'user'
        ).annotate(
            remaining_days=ExpressionWrapper(
                F('plan_expires_at') - timezone.now(),
                output_field=DurationField()
            ),
            product_count=Count('products', filter=Q(products__is_active=True)),
            order_count=Count('orders', filter=Q(
                orders__created_at__gte=timezone.now() - timedelta(days=30)
            )),
            revenue=Sum('orders__total_price', filter=Q(
                orders__is_paid=True,
                orders__created_at__gte=timezone.now() - timedelta(days=30)
            ))
        )
    
    def active_subscriptions(self):
        """فروشگاه‌های با اشتراک فعال"""
        return self.filter(
            is_active=True,
            current_plan__isnull=False,
            plan_expires_at__gt=timezone.now()
        )
    
    def expiring_soon(self, days=3):
        """فروشگاه‌های در حال انقضا"""
        return self.filter(
            is_active=True,
            current_plan__isnull=False,
            plan_expires_at__gt=timezone.now(),
            plan_expires_at__lte=timezone.now() + timedelta(days=days)
        )
    
    def expired(self):
        """فروشگاه‌های منقضی شده"""
        return self.filter(
            is_active=True,
            current_plan__isnull=False,
            plan_expires_at__lte=timezone.now()
        )


class ShopManager(models.Manager):
    """مدیر سفارشی برای Shop"""
    
    def get_queryset(self):
        return ShopQuerySet(self.model, using=self._db)
    
    def with_subscription_info(self):
        return self.get_queryset().with_subscription_info()
    
    def active_subscriptions(self):
        return self.get_queryset().active_subscriptions()
    
    def expiring_soon(self, days=3):
        return self.get_queryset().expiring_soon(days)
    
    def expired(self):
        return self.get_queryset().expired()


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
    logo = models.ImageField(upload_to='shop_logos/%Y/%m/', blank=True, null=True, verbose_name="لوگو")
    
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
    current_plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True, blank=True, 
                                    verbose_name="پلن فعال", related_name='shops')
    plan_started_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ شروع اشتراک")
    plan_expires_at = models.DateTimeField(null=True, blank=True, verbose_name="تاریخ انقضای اشتراک")

    # اطلاعات سیستمی
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ تاسیس")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین تغییر")
    
    # مدیر سفارشی
    objects = ShopManager()

    class Meta:
        verbose_name = "فروشگاه"
        verbose_name_plural = "فروشگاه‌ها"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug', 'is_active']),
            models.Index(fields=['instagram_username']),
            models.Index(fields=['created_at']),
            models.Index(fields=['plan_expires_at']),
            models.Index(fields=['current_plan', 'plan_expires_at']),
        ]

    def __str__(self):
        return f"{self.shop_name} (@{self.instagram_username})"

    def save(self, *args, **kwargs):
        """ذخیره با منطق اختصاص خودکار پلن"""
        from django.db import transaction
        
        with transaction.atomic():
            # 🔧 تولید Slug با در نظر گرفتن race condition
            if not self.slug:
                base_slug = slugify(self.instagram_username.replace('@', ''), allow_unicode=True)
                if not base_slug or len(base_slug) < 2:
                    base_slug = f"shop-{self.user.id if self.user else uuid.uuid4().hex[:8]}"
                
                slug = base_slug
                counter = 1
                
                # استفاده از select_for_update برای جلوگیری از duplicate
                while Shop.objects.select_for_update().filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                    if counter > 100:  # جلوگیری از لوپ بی‌نهایت
                        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"
                        break
                self.slug = slug

            # 🔧 اختصاص خودکار پلن برای فروشگاه‌های جدید
            is_new = self._state.adding
            
            if is_new and not self.current_plan:
                # 🎯 اولویت‌بندی برای یافتن پلن مناسب:
                # 1. پلن free فعال با حداقل 5 روز
                # 2. پلن پیش‌فرض فعال
                # 3. اولین پلن فعال
                
                free_plan = Plan.objects.select_for_update().filter(
                    code=Plan.PLAN_FREE,
                    is_active=True,
                    days__gte=5  # حداقل 5 روز
                ).first()
                
                if not free_plan:
                    free_plan = Plan.objects.select_for_update().filter(
                        is_default=True,
                        is_active=True,
                        days__gte=1
                    ).first()
                
                if not free_plan:
                    free_plan = Plan.objects.select_for_update().filter(
                        is_active=True,
                        days__gte=1
                    ).order_by('price').first()
                
                if free_plan:
                    self.current_plan = free_plan
                    self.plan_started_at = timezone.now()
                    self.plan_expires_at = self.plan_started_at + timedelta(days=free_plan.days)
                    
                    # لاگ برای دیباگ
                    print(f"🎯 فروشگاه جدید '{self.shop_name}' - پلن: {free_plan.name} ({free_plan.days} روز)")
            
            # 🔧 اگر پلن تغییر کرده، تاریخ‌ها را ریست کن
            elif not is_new and self.current_plan and self.pk:
                try:
                    old_shop = Shop.objects.get(pk=self.pk)
                    if old_shop.current_plan != self.current_plan:
                        # پلن تغییر کرده - تاریخ‌ها را به روز کن
                        self.plan_started_at = timezone.now()
                        self.plan_expires_at = self.plan_started_at + timedelta(days=self.current_plan.days)
                except Shop.DoesNotExist:
                    pass
            
            super().save(*args, **kwargs)

    def clean(self):
        """اعتبارسنجی فروشگاه"""
        super().clean()
        
        # بررسی تاریخ‌های پلن
        if self.plan_started_at and self.plan_expires_at:
            if self.plan_expires_at <= self.plan_started_at:
                raise ValidationError({
                    'plan_expires_at': 'تاریخ انقضا باید بعد از تاریخ شروع باشد'
                })
        
        # بررسی پلن
        if self.current_plan and self.current_plan.days < 1:
            raise ValidationError({
                'current_plan': f'پلن "{self.current_plan.name}" مدت زمان نامعتبر دارد'
            })
        
        # بررسی instagram username
        if self.instagram_username and not self.instagram_username.startswith('@'):
            self.instagram_username = '@' + self.instagram_username

    # ----------------------------------------
    # Properties برای دسترسی آسان
    # ----------------------------------------
    
    @property
    def remaining_days(self):
        """تعداد روزهای باقی‌مانده از اشتراک"""
        if self.plan_expires_at:
            delta = self.plan_expires_at - timezone.now()
            return max(delta.days, 0)
        return 0
    
    @property
    def remaining_days_percent(self):
        """درصد مانده از اشتراک"""
        if not self.current_plan or not self.plan_started_at or not self.plan_expires_at:
            return 0
        
        total_days = self.current_plan.days
        remaining = self.remaining_days
        
        if total_days > 0:
            return int((remaining / total_days) * 100)
        return 0

    @property
    def is_subscription_active(self):
        """آیا اشتراک فروشگاه معتبر است؟"""
        if not self.is_active:
            return False
        if not self.current_plan or not self.plan_expires_at:
            return False
        return timezone.now() < self.plan_expires_at
    
    @property 
    def subscription_status(self):
        """وضعیت اشتراک به صورت متن"""
        if not self.current_plan:
            return 'بدون پلن'
        elif self.is_subscription_active:
            return 'فعال'
        else:
            return 'منقضی شده'
    
    @property
    def subscription_status_color(self):
        """رنگ وضعیت اشتراک برای نمایش"""
        if not self.current_plan:
            return 'secondary'
        elif self.is_subscription_active:
            if self.remaining_days > 30:
                return 'success'
            elif self.remaining_days > 7:
                return 'warning'
            else:
                return 'danger'
        else:
            return 'dark'

    # ----------------------------------------
    # متدهای منطقی
    # ----------------------------------------
    
    def can_add_product(self):
        """آیا مجاز به افزودن محصول جدید است؟"""
        if not self.is_subscription_active:
            return False
        
        # استفاده از annotate برای کارایی بهتر
        from django.db.models import Count
        product_count = self.products.filter(is_active=True).count()
        
        return product_count < self.current_plan.max_products

    def can_accept_order(self):
        """آیا سقف سفارش ماهانه پر نشده است؟"""
        if not self.is_subscription_active:
            return False
        
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        order_count = self.orders.filter(
            created_at__gte=current_month_start
        ).count()
        
        return order_count < self.current_plan.max_orders_per_month

    def renew_subscription(self, new_plan, start_from_now=True):
        """
        تمدید یا ارتقای اشتراک
        """
        if not new_plan.is_active:
            raise ValidationError(f"پلن {new_plan.name} غیرفعال است")
        
        now = timezone.now()
        
        if start_from_now or not self.plan_expires_at or self.plan_expires_at < now:
            # شروع از الان
            self.plan_started_at = now
            self.plan_expires_at = now + timedelta(days=new_plan.days)
        else:
            # ادامه از تاریخ انقضای قبلی
            self.plan_expires_at = self.plan_expires_at + timedelta(days=new_plan.days)
        
        self.current_plan = new_plan
        self.save()
        
        return True

    def extend_subscription(self, additional_days):
        """
        تمدید اشتراک به تعداد روز مشخص
        """
        if not self.current_plan:
            raise ValidationError("فروشگاه پلن فعال ندارد")
        
        if not self.plan_expires_at:
            self.plan_expires_at = timezone.now()
        
        self.plan_expires_at += timedelta(days=additional_days)
        self.save()
        
        return True

    def get_usage_stats(self):
        """دریافت آمار استفاده از پلن"""
        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        
        return {
            'products': {
                'current': self.products.filter(is_active=True).count(),
                'max': self.current_plan.max_products if self.current_plan else 0,
                'remaining': max(0, (self.current_plan.max_products if self.current_plan else 0) - 
                               self.products.filter(is_active=True).count())
            },
            'orders': {
                'current': self.orders.filter(created_at__gte=current_month_start).count(),
                'max': self.current_plan.max_orders_per_month if self.current_plan else 0,
                'remaining': max(0, (self.current_plan.max_orders_per_month if self.current_plan else 0) - 
                               self.orders.filter(created_at__gte=current_month_start).count())
            }
        }

    def get_subscription_timeline(self):
        """تاریخچه و آینده اشتراک"""
        if not self.current_plan:
            return []
        
        timeline = []
        now = timezone.now()
        
        # گذشته
        if self.plan_started_at:
            timeline.append({
                'date': self.plan_started_at,
                'event': 'شروع اشتراک',
                'plan': self.current_plan.name,
                'type': 'start'
            })
        
        # حال
        timeline.append({
            'date': now,
            'event': 'امروز',
            'days_remaining': self.remaining_days,
            'type': 'current'
        })
        
        # آینده
        if self.plan_expires_at:
            timeline.append({
                'date': self.plan_expires_at,
                'event': 'انقضای اشتراک',
                'plan': self.current_plan.name,
                'type': 'expiry'
            })
        
        return sorted(timeline, key=lambda x: x['date'])

    # ----------------------------------------
    # متدهای کمکی برای دیباگ و نمایش
    # ----------------------------------------
    
    def debug_info(self):
        """اطلاعات دیباگ برای نمایش در ادمین"""
        info = []
        
        info.append(f"فروشگاه: {self.shop_name}")
        info.append(f"Slug: {self.slug}")
        info.append(f"وضعیت: {'فعال' if self.is_active else 'غیرفعال'}")
        
        if self.current_plan:
            info.append(f"پلن: {self.current_plan.name}")
            info.append(f"روزهای پلن: {self.current_plan.days}")
            info.append(f"شروع اشتراک: {self.plan_started_at}")
            info.append(f"انقضای اشتراک: {self.plan_expires_at}")
            info.append(f"روزهای باقی‌مانده: {self.remaining_days}")
            info.append(f"وضعیت اشتراک: {self.subscription_status}")
            info.append(f"می‌تواند محصول اضافه کند: {'بله' if self.can_add_product() else 'خیر'}")
            info.append(f"می‌تواند سفارش بگیرد: {'بله' if self.can_accept_order() else 'خیر'}")
        else:
            info.append("پلن: ندارد")
        
        return "\n".join(info)
    
    def to_dict(self):
        """تبدیل به دیکشنری برای API"""
        return {
            'id': self.id,
            'shop_name': self.shop_name,
            'slug': self.slug,
            'instagram_username': self.instagram_username,
            'is_active': self.is_active,
            'current_plan': {
                'id': self.current_plan.id if self.current_plan else None,
                'name': self.current_plan.name if self.current_plan else None,
                'code': self.current_plan.code if self.current_plan else None,
            } if self.current_plan else None,
            'plan_started_at': self.plan_started_at.isoformat() if self.plan_started_at else None,
            'plan_expires_at': self.plan_expires_at.isoformat() if self.plan_expires_at else None,
            'remaining_days': self.remaining_days,
            'is_subscription_active': self.is_subscription_active,
            'subscription_status': self.subscription_status,
            'created_at': self.created_at.isoformat(),
        }