"""
سیگنال‌های مرتبط با فروشگاه و سیستم اشتراک
برای خودکارسازی فرآیندها
"""

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from datetime import timedelta
import logging

from .models import Shop, Plan, ShopActivity, ShopErrorLog
from logs.models import AdminLog

logger = logging.getLogger('instastore')

# ------------------------------------------------------------
# 1. سیگنال‌های مربوط به مدل Shop
# ------------------------------------------------------------

@receiver(pre_save, sender=Shop)
def validate_shop_before_save(sender, instance, **kwargs):
    """
    اعتبارسنجی فروشگاه قبل از ذخیره
    """
    # بررسی تاریخ‌های پلن
    if instance.plan_started_at and instance.plan_expires_at:
        if instance.plan_expires_at <= instance.plan_started_at:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                'plan_expires_at': 'تاریخ انقضا باید بعد از تاریخ شروع باشد'
            })
    
    # بررسی days پلن
    if instance.current_plan and instance.current_plan.days < 1:
        from django.core.exceptions import ValidationError
        raise ValidationError({
            'current_plan': f'پلن "{instance.current_plan.name}" مدت زمان نامعتبر دارد'
        })
    
    # بررسی instagram username
    if instance.instagram_username and not instance.instagram_username.startswith('@'):
        instance.instagram_username = '@' + instance.instagram_username


@receiver(post_save, sender=Shop)
def handle_shop_post_save(sender, instance, created, **kwargs):
    """
    پس از ذخیره فروشگاه
    """
    if created:
        # فروشگاه جدید ایجاد شده
        logger.info(f"🎉 فروشگاه جدید ایجاد شد: {instance.shop_name} ({instance.slug})")
        
        # ارسال ایمیل خوش‌آمدگویی
        if instance.user and instance.user.email:
            try:
                send_welcome_email(instance)
            except Exception as e:
                logger.error(f"Failed to send welcome email: {str(e)}")
        
        # ثبت فعالیت
        ShopActivity.objects.create(
            shop=instance,
            action='SHOP_CREATED',
            details=f'فروشگاه {instance.shop_name} ایجاد شد'
        )
    
    else:
        # فروشگاه آپدیت شده
        logger.info(f"🔄 فروشگاه آپدیت شد: {instance.shop_name}")
        
        # اگر پلن تغییر کرده
        try:
            old_instance = Shop.objects.get(pk=instance.pk)
            if old_instance.current_plan != instance.current_plan:
                ShopActivity.objects.create(
                    shop=instance,
                    action='PLAN_CHANGED',
                    details=f'پلن از {old_instance.current_plan} به {instance.current_plan} تغییر کرد'
                )
        except Shop.DoesNotExist:
            pass


@receiver(pre_delete, sender=Shop)
def handle_shop_pre_delete(sender, instance, **kwargs):
    """
    قبل از حذف فروشگاه
    """
    # ثبت لاگ
    logger.warning(f"🗑️ فروشگاه در حال حذف است: {instance.shop_name}")
    
    # ثبت فعالیت
    ShopActivity.objects.create(
        shop=instance,
        action='SHOP_DELETED',
        details=f'فروشگاه {instance.shop_name} حذف شد'
    )


# ------------------------------------------------------------
# 2. سیگنال‌های مربوط به سیستم اشتراک
# ------------------------------------------------------------

@receiver(post_save, sender=Shop)
def handle_subscription_changes(sender, instance, created, **kwargs):
    """
    مدیریت تغییرات اشتراک
    """
    if not created and instance.plan_expires_at:
        # بررسی انقضای اشتراک
        handle_subscription_expiry(instance)
        
        # بررسی نزدیک بودن به انقضا
        handle_expiry_warnings(instance)


def handle_subscription_expiry(shop):
    """
    بررسی و مدیریت انقضای اشتراک
    """
    now = timezone.now()
    
    # اگر اشتراک منقضی شده
    if shop.plan_expires_at <= now:
        # فقط یک بار در روز چک کن
        last_check = getattr(shop, '_last_expiry_check', None)
        
        if not last_check or (now - last_check).days >= 1:
            logger.info(f"⏰ اشتراک فروشگاه {shop.shop_name} منقضی شده است")
            
            # ثبت فعالیت
            ShopActivity.objects.create(
                shop=shop,
                action='SUBSCRIPTION_EXPIRED',
                details='اشتراک فروشگاه منقضی شد'
            )
            
            # ارسال اعلان به صاحب فروشگاه
            if shop.user and shop.user.email:
                try:
                    send_expiry_notification(shop)
                except Exception as e:
                    logger.error(f"Failed to send expiry notification: {str(e)}")
            
            shop._last_expiry_check = now


def handle_expiry_warnings(shop):
    """
    ارسال هشدار قبل از انقضای اشتراک
    """
    now = timezone.now()
    remaining_days = (shop.plan_expires_at - now).days
    
    # هشدار برای 7، 3 و 1 روز مانده
    warning_days = [7, 3, 1]
    
    if remaining_days in warning_days and remaining_days > 0:
        # بررسی که قبلاً هشدار ارسال نشده باشد
        warning_sent_key = f'expiry_warning_{remaining_days}_sent'
        
        if not getattr(shop, warning_sent_key, False):
            logger.info(
                f"⚠️ هشدار انقضا: {shop.shop_name} - {remaining_days} روز باقی مانده"
            )
            
            # ثبت فعالیت
            ShopActivity.objects.create(
                shop=shop,
                action='SUBSCRIPTION_WARNING',
                details=f'هشدار انقضا: {remaining_days} روز باقی مانده'
            )
            
            # ارسال اعلان
            if shop.user and shop.user.email:
                try:
                    send_expiry_warning_email(shop, remaining_days)
                except Exception as e:
                    logger.error(f"Failed to send expiry warning: {str(e)}")
            
            setattr(shop, warning_sent_key, True)


# ------------------------------------------------------------
# 3. سیگنال‌های مربوط به پلن‌ها
# ------------------------------------------------------------

@receiver(pre_save, sender=Plan)
def validate_plan_before_save(sender, instance, **kwargs):
    """
    اعتبارسنجی پلن قبل از ذخیره
    """
    if instance.days <= 0:
        from django.core.exceptions import ValidationError
        raise ValidationError({'days': 'مدت اعتبار باید بیشتر از صفر باشد'})
    
    if instance.code == Plan.PLAN_FREE and instance.price > 0:
        from django.core.exceptions import ValidationError
        raise ValidationError({'price': 'پلن رایگان باید قیمت صفر داشته باشد'})


@receiver(post_save, sender=Plan)
def handle_plan_post_save(sender, instance, created, **kwargs):
    """
    پس از ذخیره پلن
    """
    if created:
        logger.info(f"📋 پلن جدید ایجاد شد: {instance.name}")
    else:
        logger.info(f"🔄 پلن آپدیت شد: {instance.name}")
        
        # اگر پلن غیرفعال شده، به فروشگاه‌ها اطلاع بده
        if not instance.is_active:
            # پیدا کردن فروشگاه‌هایی که از این پلن استفاده می‌کنند
            shops = instance.shops.all()
            if shops.exists():
                logger.warning(
                    f"⚠️ پلن {instance.name} غیرفعال شد. "
                    f"{shops.count()} فروشگاه تحت تأثیر قرار می‌گیرند."
                )


# ------------------------------------------------------------
# 4. سیگنال‌های مربوط به فعالیت‌ها
# ------------------------------------------------------------

@receiver(post_save, sender=ShopActivity)
def log_shop_activity(sender, instance, created, **kwargs):
    """
    لاگ فعالیت‌های فروشگاه
    """
    if created and instance.action in ['ORDER_CREATED', 'PLAN_CHANGED', 'SHOP_CREATED']:
        logger.info(f"📝 فعالیت فروشگاه: {instance.shop.slug} - {instance.action}")


@receiver(post_save, sender=ShopErrorLog)
def handle_shop_error(sender, instance, created, **kwargs):
    """
    مدیریت خطاهای فروشگاه
    """
    if created:
        logger.error(f"❌ خطای فروشگاه {instance.shop.slug}: {instance.error_message}")
        
        # اگر خطا بحرانی است، به ادمین اطلاع بده
        if instance.error_message and 'critical' in instance.error_message.lower():
            notify_admin_critical_error(instance)


# ------------------------------------------------------------
# 5. سیگنال‌های کاربردی
# ------------------------------------------------------------

@receiver(post_save, sender=User)
def create_shop_for_seller(sender, instance, created, **kwargs):
    """
    ایجاد خودکار فروشگاه برای کاربرانی که نقش فروشنده دارند
    """
    if created and instance.groups.filter(name='sellers').exists():
        # اگر کاربر در گروه فروشنده‌ها است
        try:
            Shop.objects.create(
                user=instance,
                shop_name=f"فروشگاه {instance.username}",
                instagram_username=f"@{instance.username}",
                phone_number="",
                is_active=True
            )
            logger.info(f"🛍️ فروشگاه خودکار برای کاربر {instance.username} ایجاد شد")
        except Exception as e:
            logger.error(f"Failed to create auto shop: {str(e)}")


# ------------------------------------------------------------
# 6. توابع کمکی برای ارسال ایمیل
# ------------------------------------------------------------

def send_welcome_email(shop):
    """
    ارسال ایمیل خوش‌آمدگویی
    """
    subject = f"🎉 به پلتفرم ما خوش آمدید، {shop.shop_name}!"
    
    context = {
        'shop': shop,
        'plan': shop.current_plan,
        'expiry_date': shop.plan_expires_at,
        'remaining_days': shop.remaining_days,
        'dashboard_url': f"{settings.SITE_URL}/seller/dashboard/",
        'plans_url': f"{settings.SITE_URL}/seller/plans/",
    }
    
    message = render_to_string('emails/welcome_seller.html', context)
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[shop.user.email],
        html_message=message,
        fail_silently=True
    )
    
    logger.info(f"📧 ایمیل خوش‌آمد به {shop.user.email} ارسال شد")


def send_expiry_notification(shop):
    """
    ارسال اعلان انقضای اشتراک
    """
    subject = f"⏰ اشتراک فروشگاه شما منقضی شده است"
    
    context = {
        'shop': shop,
        'plan': shop.current_plan,
        'renew_url': f"{settings.SITE_URL}/seller/plans/",
    }
    
    message = render_to_string('emails/subscription_expired.html', context)
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[shop.user.email],
        html_message=message,
        fail_silently=True
    )


def send_expiry_warning_email(shop, remaining_days):
    """
    ارسال هشدار انقضای اشتراک
    """
    subject = f"⚠️ فقط {remaining_days} روز تا انقضای اشتراک شما باقی مانده است"
    
    context = {
        'shop': shop,
        'remaining_days': remaining_days,
        'plan': shop.current_plan,
        'expiry_date': shop.plan_expires_at,
        'renew_url': f"{settings.SITE_URL}/seller/plans/",
    }
    
    message = render_to_string('emails/expiry_warning.html', context)
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[shop.user.email],
        html_message=message,
        fail_silently=True
    )
    
    logger.info(f"📧 هشدار انقضا ({remaining_days} روز) به {shop.user.email} ارسال شد")


def notify_admin_critical_error(error_log):
    """
    اطلاع به ادمین درباره خطای بحرانی
    """
    subject = f"🚨 خطای بحرانی در فروشگاه {error_log.shop.slug}"
    
    context = {
        'error': error_log,
        'shop': error_log.shop,
        'admin_url': f"{settings.SITE_URL}/admin/logs/shoperrorlog/{error_log.id}/change/",
    }
    
    message = render_to_string('emails/admin_critical_error.html', context)
    
    # ارسال به ادمین‌ها
    admins = User.objects.filter(is_staff=True, is_active=True)
    recipient_list = [admin.email for admin in admins if admin.email]
    
    if recipient_list:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=message,
            fail_silently=True
        )
        
        logger.info(f"🚨 اطلاع خطای بحرانی به {len(recipient_list)} ادمین ارسال شد")


# ------------------------------------------------------------
# 7. Utility functions
# ------------------------------------------------------------

def check_daily_expirations():
    """
    بررسی روزانه انقضای اشتراک‌ها
    این تابع باید توسط Celery یا cron اجرا شود
    """
    from datetime import datetime, timedelta
    
    now = timezone.now()
    
    # فروشگاه‌های که امروز منقضی می‌شوند
    expiring_today = Shop.objects.filter(
        plan_expires_at__date=now.date(),
        is_active=True
    )
    
    # فروشگاه‌های که دیروز منقضی شده‌اند
    expired_yesterday = Shop.objects.filter(
        plan_expires_at__date=(now - timedelta(days=1)).date(),
        is_active=True
    )
    
    # لاگ کردن
    if expiring_today.exists():
        logger.info(f"📅 {expiring_today.count()} فروشگاه امروز منقضی می‌شوند")
    
    if expired_yesterday.exists():
        logger.info(f"📅 {expired_yesterday.count()} فروشگاه دیروز منقضی شده‌اند")
    
    return {
        'expiring_today': expiring_today.count(),
        'expired_yesterday': expired_yesterday.count(),
    }


# ------------------------------------------------------------
# 8. ثبت سیگنال‌ها
# ------------------------------------------------------------

def ready():
    """
    ثبت سیگنال‌ها هنگام لود اپ
    """
    # این تابع در apps.py صدا زده می‌شود
    pass