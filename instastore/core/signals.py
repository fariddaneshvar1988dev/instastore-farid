"""
سیگنال‌های مرکزی پلتفرم
برای هماهنگی بین ماژول‌های مختلف
"""

from django.db.models.signals import post_save, pre_save, post_delete, pre_delete
from django.dispatch import receiver, Signal
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import logging

from shops.models import Shop, Plan
from products.models import Product, Category
from orders.models import Order
from customers.models import Customer
from logs.models import AdminLog, SystemLog, ShopActivityLog

logger = logging.getLogger('instastore')

# ------------------------------------------------------------
# 1. سیگنال‌های سفارشی پلتفرم
# ------------------------------------------------------------

# سیگنال‌های مربوط به اشتراک
subscription_created = Signal()  # اشتراک ایجاد شد
subscription_updated = Signal()  # اشتراک آپدیت شد
subscription_expired = Signal()  # اشتراک منقضی شد
subscription_renewed = Signal()  # اشتراک تمدید شد

# سیگنال‌های مربوط به فروشگاه
shop_created = Signal()  # فروشگاه ایجاد شد
shop_updated = Signal()  # فروشگاه آپدیت شد
shop_deactivated = Signal()  # فروشگاه غیرفعال شد
shop_reactivated = Signal()  # فروشگاه مجدد فعال شد

# سیگنال‌های مربوط به تراکنش‌ها
payment_successful = Signal()  # پرداخت موفق
payment_failed = Signal()  # پرداخت ناموفق
payment_refunded = Signal()  # پرداخت برگشت خورد

# سیگنال‌های اعلان
notification_sent = Signal()  # اعلان ارسال شد
email_sent = Signal()  # ایمیل ارسال شد
sms_sent = Signal()  # SMS ارسال شد

# ------------------------------------------------------------
# 2. سیگنال‌های مربوط به User
# ------------------------------------------------------------

@receiver(post_save, sender=User)
def handle_user_post_save(sender, instance, created, **kwargs):
    """
    مدیریت ذخیره کاربر
    """
    if created:
        logger.info(f"👤 کاربر جدید ایجاد شد: {instance.username}")
        
        # ثبت لاگ سیستم
        SystemLog.info(
            f"User created: {instance.username} ({instance.email})",
            component='AUTH',
            data={
                'username': instance.username,
                'email': instance.email,
                'is_staff': instance.is_staff,
                'is_superuser': instance.is_superuser
            }
        )
    
    else:
        # اگر کاربر غیرفعال شده
        if not instance.is_active and instance.pk:
            try:
                old_user = User.objects.get(pk=instance.pk)
                if old_user.is_active and not instance.is_active:
                    logger.warning(f"👤 کاربر غیرفعال شد: {instance.username}")
                    
                    # غیرفعال کردن فروشگاه مرتبط
                    if hasattr(instance, 'shop'):
                        shop = instance.shop
                        shop.is_active = False
                        shop.save()
                        
                        SystemLog.warning(
                            f"User deactivated: {instance.username}, shop {shop.slug} also deactivated",
                            component='AUTH'
                        )
            except User.DoesNotExist:
                pass


@receiver(pre_delete, sender=User)
def handle_user_pre_delete(sender, instance, **kwargs):
    """
    قبل از حذف کاربر
    """
    logger.warning(f"🗑️ کاربر در حال حذف است: {instance.username}")
    
    # ثبت لاگ
    AdminLog.objects.create(
        admin=instance,
        action='USER_DELETED',
        model='User',
        object_id=instance.id,
        description=f'User {instance.username} is being deleted'
    )


# ------------------------------------------------------------
# 3. سیگنال‌های مربوط به Shop
# ------------------------------------------------------------

@receiver(post_save, sender=Shop)
def emit_shop_signals(sender, instance, created, **kwargs):
    """
    ارسال سیگنال‌های مربوط به فروشگاه
    """
    if created:
        # فروشگاه جدید
        shop_created.send(
            sender=Shop,
            shop=instance,
            user=instance.user,
            timestamp=timezone.now()
        )
        
        logger.info(f"🛍️ سیگنال shop_created برای {instance.slug} ارسال شد")
        
    else:
        # فروشگاه آپدیت شده
        shop_updated.send(
            sender=Shop,
            shop=instance,
            changes=kwargs.get('update_fields', []),
            timestamp=timezone.now()
        )
        
        # بررسی تغییرات مهم
        try:
            old_shop = Shop.objects.get(pk=instance.pk)
            
            # اگر is_active تغییر کرده
            if old_shop.is_active != instance.is_active:
                if instance.is_active:
                    shop_reactivated.send(
                        sender=Shop,
                        shop=instance,
                        timestamp=timezone.now()
                    )
                    logger.info(f"🔓 فروشگاه فعال شد: {instance.slug}")
                else:
                    shop_deactivated.send(
                        sender=Shop,
                        shop=instance,
                        timestamp=timezone.now()
                    )
                    logger.warning(f"🔒 فروشگاه غیرفعال شد: {instance.slug}")
            
            # اگر پلن تغییر کرده
            if old_shop.current_plan != instance.current_plan:
                if instance.current_plan:
                    subscription_renewed.send(
                        sender=Shop,
                        shop=instance,
                        old_plan=old_shop.current_plan,
                        new_plan=instance.current_plan,
                        timestamp=timezone.now()
                    )
                    logger.info(f"🔄 پلن فروشگاه تغییر کرد: {instance.slug}")
                    
        except Shop.DoesNotExist:
            pass


@receiver(pre_save, sender=Shop)
def check_subscription_expiry_before_save(sender, instance, **kwargs):
    """
    بررسی انقضای اشتراک قبل از ذخیره
    """
    if instance.pk and instance.plan_expires_at:
        try:
            old_shop = Shop.objects.get(pk=instance.pk)
            
            # اگر تاریخ انقضا گذشته و فروشگاه هنوز فعال است
            now = timezone.now()
            if (old_shop.plan_expires_at > now and 
                instance.plan_expires_at <= now and 
                instance.is_active):
                
                # ارسال سیگنال انقضا
                subscription_expired.send(
                    sender=Shop,
                    shop=instance,
                    expired_at=instance.plan_expires_at,
                    timestamp=timezone.now()
                )
                
                logger.warning(f"⏰ اشتراک منقضی شد: {instance.slug}")
                
                # ثبت فعالیت
                ShopActivityLog.log_activity(
                    shop=instance,
                    action='SUBSCRIPTION_EXPIRED',
                    category='PLAN',
                    user=instance.user,
                    details={
                        'expired_at': instance.plan_expires_at.isoformat(),
                        'plan_name': instance.current_plan.name if instance.current_plan else 'None'
                    }
                )
                
        except Shop.DoesNotExist:
            pass


# ------------------------------------------------------------
# 4. سیگنال‌های مربوط به Plan
# ------------------------------------------------------------

@receiver(post_save, sender=Plan)
def handle_plan_changes(sender, instance, created, **kwargs):
    """
    مدیریت تغییرات پلن
    """
    if created:
        logger.info(f"📋 پلن جدید ایجاد شد: {instance.name}")
        
        # اگر پلن پیش‌فرض است
        if instance.is_default:
            SystemLog.info(
                f"New default plan created: {instance.name}",
                component='PLAN',
                data={
                    'plan_id': instance.id,
                    'plan_name': instance.name,
                    'price': instance.price,
                    'days': instance.days
                }
            )
    
    else:
        # اگر پلن غیرفعال شده
        if not instance.is_active and instance.pk:
            try:
                old_plan = Plan.objects.get(pk=instance.pk)
                if old_plan.is_active and not instance.is_active:
                    logger.warning(f"📋 پلن غیرفعال شد: {instance.name}")
                    
                    # پیدا کردن فروشگاه‌هایی که از این پلن استفاده می‌کنند
                    affected_shops = instance.shops.count()
                    if affected_shops > 0:
                        SystemLog.warning(
                            f"Plan deactivated: {instance.name}, affecting {affected_shops} shops",
                            component='PLAN'
                        )
            except Plan.DoesNotExist:
                pass


# ------------------------------------------------------------
# 5. سیگنال‌های مربوط به Product
# ------------------------------------------------------------

@receiver(post_save, sender=Product)
def handle_product_changes(sender, instance, created, **kwargs):
    """
    مدیریت تغییرات محصول
    """
    if instance.shop:
        action = 'PRODUCT_CREATED' if created else 'PRODUCT_UPDATED'
        
        ShopActivityLog.log_activity(
            shop=instance.shop,
            action=action,
            category='PRODUCT',
            user=instance.shop.user,
            details={
                'product_id': instance.id,
                'product_name': instance.name,
                'price': str(instance.base_price),
                'is_active': instance.is_active
            }
        )


@receiver(pre_delete, sender=Product)
def handle_product_deletion(sender, instance, **kwargs):
    """
    قبل از حذف محصول
    """
    if instance.shop:
        ShopActivityLog.log_activity(
            shop=instance.shop,
            action='PRODUCT_DELETED',
            category='PRODUCT',
            user=instance.shop.user,
            details={
                'product_id': instance.id,
                'product_name': instance.name
            }
        )


# ------------------------------------------------------------
# 6. سیگنال‌های مربوط به Order
# ------------------------------------------------------------

@receiver(post_save, sender=Order)
def handle_order_changes(sender, instance, created, **kwargs):
    """
    مدیریت تغییرات سفارش
    """
    if instance.shop:
        action = 'ORDER_CREATED' if created else 'ORDER_UPDATED'
        
        # ثبت فعالیت
        ShopActivityLog.log_activity(
            shop=instance.shop,
            action=action,
            category='ORDER',
            user=instance.user if instance.user else None,
            details={
                'order_id': instance.id,
                'order_number': instance.order_number,
                'total_price': str(instance.total_price),
                'status': instance.status,
                'is_paid': instance.is_paid
            }
        )
        
        # اگر سفارش پرداخت شده
        if instance.is_paid and not created:
            payment_successful.send(
                sender=Order,
                order=instance,
                amount=instance.total_price,
                timestamp=timezone.now()
            )
            
            logger.info(f"💰 پرداخت موفق برای سفارش {instance.order_number}")


# ------------------------------------------------------------
# 7. سیگنال‌های مربوط به Customer
# ------------------------------------------------------------

@receiver(post_save, sender=Customer)
def handle_customer_changes(sender, instance, created, **kwargs):
    """
    مدیریت تغییرات مشتری
    """
    if instance.shop:
        action = 'CUSTOMER_CREATED' if created else 'CUSTOMER_UPDATED'
        
        ShopActivityLog.log_activity(
            shop=instance.shop,
            action=action,
            category='CUSTOMER',
            user=instance.shop.user if hasattr(instance.shop, 'user') else None,
            details={
                'customer_id': instance.id,
                'phone_number': instance.phone_number,
                'total_orders': instance.total_orders,
                'total_spent': str(instance.total_spent)
            }
        )


# ------------------------------------------------------------
# 8. هندلرهای سیگنال‌های سفارشی
# ------------------------------------------------------------

@receiver(subscription_expired)
def handle_subscription_expiry(sender, shop, **kwargs):
    """
    هندلر سیگنال انقضای اشتراک
    """
    # ارسال ایمیل به صاحب فروشگاه
    if shop.user and shop.user.email:
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            
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
            
            # ارسال سیگنال email_sent
            email_sent.send(
                sender='subscription_system',
                email_type='SUBSCRIPTION_EXPIRED',
                recipient=shop.user.email,
                timestamp=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to send expiry email: {str(e)}")


@receiver(subscription_renewed)
def handle_subscription_renewal(sender, shop, old_plan, new_plan, **kwargs):
    """
    هندلر سیگنال تمدید اشتراک
    """
    logger.info(f"🎉 اشتراک تمدید شد: {shop.slug} ({old_plan.name} → {new_plan.name})")
    
    # ثبت در سیستم لاگ
    SystemLog.info(
        f"Subscription renewed: {shop.slug}",
        component='PLAN',
        data={
            'shop_slug': shop.slug,
            'old_plan': old_plan.name,
            'new_plan': new_plan.name,
            'old_price': old_plan.price,
            'new_price': new_plan.price
        }
    )


@receiver(shop_created)
def handle_new_shop(sender, shop, user, **kwargs):
    """
    هندلر سیگنال ایجاد فروشگاه جدید
    """
    # ارسال ایمیل خوش‌آمدگویی
    if user.email:
        try:
            from django.core.mail import send_mail
            
            subject = f"🎉 فروشگاه شما آماده است!"
            
            message = f"""
            سلام {user.get_full_name() or user.username},
            
            فروشگاه شما با موفقیت ایجاد شد:
            
            نام فروشگاه: {shop.shop_name}
            آدرس: {settings.SITE_URL}/shop/{shop.slug}/
            پنل مدیریت: {settings.SITE_URL}/seller/dashboard/
            
            شما {shop.current_plan.days} روز اشتراک رایگان دارید.
            
            برای شروع، محصولات خود را اضافه کنید.
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {str(e)}")


@receiver(payment_successful)
def handle_successful_payment(sender, order, amount, **kwargs):
    """
    هندلر سیگنال پرداخت موفق
    """
    # به‌روزرسانی آمار فروشگاه
    if order.shop:
        # افزایش تعداد سفارشات پرداخت شده
        order.shop.save()  # آمار در save محاسبه می‌شود
        
        logger.info(f"💰 پرداخت {amount} ریال برای فروشگاه {order.shop.slug}")


# ------------------------------------------------------------
# 9. Utility Functions
# ------------------------------------------------------------

def emit_custom_signal(signal_name, **kwargs):
    """
    ارسال سیگنال سفارشی با نام
    """
    if signal_name == 'SUBSCRIPTION_CREATED':
        subscription_created.send(sender='system', **kwargs)
    elif signal_name == 'SHOP_UPDATED':
        shop_updated.send(sender='system', **kwargs)
    elif signal_name == 'PAYMENT_FAILED':
        payment_failed.send(sender='system', **kwargs)
    elif signal_name == 'NOTIFICATION_SENT':
        notification_sent.send(sender='system', **kwargs)
    
    logger.debug(f"سیگنال {signal_name} ارسال شد")


def setup_all_signals():
    """
    راه‌اندازی همه سیگنال‌ها
    این تابع باید در ready() فراخوانی شود
    """
    logger.info("🚀 همه سیگنال‌های پلتفرم راه‌اندازی شدند")
    
    # ثبت هندلرهای اضافی
    from django.db.models.signals import m2m_changed
    
    # هندلر برای تغییرات many-to-many
    @receiver(m2m_changed)
    def handle_m2m_changes(sender, instance, action, **kwargs):
        """
        هندلر عمومی برای تغییرات m2m
        """
        if action in ['post_add', 'post_remove', 'post_clear']:
            model_name = sender.__name__
            logger.debug(f"M2M change: {model_name} - {action}")
    
    return True