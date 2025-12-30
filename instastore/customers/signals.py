from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Customer

@receiver(post_save, sender=User)
def link_user_to_customer(sender, instance, created, **kwargs):
    """
    وقتی یوزر جدید ساخته می‌شود، بررسی می‌کند آیا مشتری‌ای با این شماره موبایل
    (که همان نام کاربری است) وجود دارد یا خیر. اگر بود، متصل می‌شود.
    """
    if created:
        # فرض بر این است که username همان شماره موبایل است
        phone_number = instance.username
        
        try:
            # دنبال مشتری‌ای می‌گردیم که شماره‌اش این است ولی هنوز یوزر ندارد (خرید مهمان)
            customer = Customer.objects.get(phone_number=phone_number, user__isnull=True)
            
            # اتصال مشتری قدیمی به یوزر جدید
            customer.user = instance
            
            # اگر مشتری نام نداشت، نام یوزر را برایش ست کن
            if not customer.full_name:
                customer.full_name = f"{instance.first_name} {instance.last_name}".strip()
                
            customer.save()
            print(f"✅ User {instance.username} linked to existing Customer profile.")
            
        except Customer.DoesNotExist:
            # اگر مشتری وجود نداشت، کاری نمی‌کنیم (چون ممکن است بعداً در اولین خرید ساخته شود)
            # یا می‌توانیم همینجا یک پروفایل خالی بسازیم:
            pass