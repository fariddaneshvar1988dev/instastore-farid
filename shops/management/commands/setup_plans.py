from django.core.management.base import BaseCommand
from shops.models import Plan

class Command(BaseCommand):
    help = 'ایجاد پلن‌های پیش‌فرض اشتراک در دیتابیس'

    def handle(self, *args, **kwargs):
        # لیست پلن‌هایی که می‌خواهیم بسازیم
        plans_data = [
            {
                'code': Plan.PLAN_FREE,
                'name': 'رایگان آزمایشی (۵ روز)',
                'price': 0,
                'days': 5,                # ۵ روز رایگان
                'max_products': 10,       # محدودیت ۱۰ محصول
                'max_orders_per_month': 50,
                'is_default': True,       # این پلن پیش‌فرض ثبت‌نام است
                'description': 'مناسب برای تست سیستم و راه‌اندازی اولیه فروشگاه.'
            },
            {
                'code': Plan.PLAN_BASIC,
                'name': 'پایه – ماهانه',
                'price': 150000,          # ۱۵۰ هزار تومان
                'days': 30,
                'max_products': 50,
                'max_orders_per_month': 200,
                'is_default': False,
                'description': 'برای فروشگاه‌های کوچک و نوپا.'
            },
            {
                'code': Plan.PLAN_PRO,
                'name': 'حرفه‌ای – ماهانه',
                'price': 300000,          # ۳۰۰ هزار تومان
                'days': 30,
                'max_products': 500,      # تعداد محصول بالا
                'max_orders_per_month': 2000,
                'is_default': False,
                'description': 'امکانات کامل برای فروشگاه‌های در حال رشد.'
            },
        ]

        for data in plans_data:
            # از دیکشنری جدا می‌کنیم تا به عنوان defaults بفرستیم
            code = data.pop('code')
            
            plan, created = Plan.objects.get_or_create(
                code=code,
                defaults=data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f"پلن '{plan.name}' با موفقیت ساخته شد."))
            else:
                # اگر پلن وجود داشت، اطلاعاتش را آپدیت می‌کنیم (اختیاری)
                for key, value in data.items():
                    setattr(plan, key, value)
                plan.save()
                self.stdout.write(self.style.WARNING(f"پلن '{plan.name}' بروزرسانی شد."))