# logs/signals.py
"""
سیگنال‌های ماژول لاگ‌گیری
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from shops.models import Shop
from .models import SystemLog

@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    """ثبت لاگ فعالیت کاربر"""
    if created:
        SystemLog.info(
            f"User created: {instance.username}",
            component='AUTH',
            data={'username': instance.username, 'email': instance.email}
        )

@receiver(post_save, sender=Shop)
def log_shop_activity(sender, instance, created, **kwargs):
    """ثبت لاگ فعالیت فروشگاه"""
    action = 'created' if created else 'updated'
    SystemLog.info(
        f"Shop {action}: {instance.shop_name}",
        component='SHOP',
        data={'shop_slug': instance.slug, 'action': action}
    )