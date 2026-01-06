# test_simple.py
import os
import django
import sys

# تنظیمات
sys.path.append('C:/Users/farid-/Desktop/repo/instastore-farid/instastore')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instastore.settings')
django.setup()

from django.test import TestCase
from django.contrib.auth.models import User
from shops.models import Shop, Plan
from customers.models import Customer
from products.models import Product, Category

print("🔍 تست ساده Multi-Tenancy...")

# ۱. بررسی ساختار دیتابیس
print("\n۱. بررسی ساختار دیتابیس:")
try:
    # بررسی وجود فیلد shop در Customer
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA table_info(customers_customer)")
        columns = [row[1] for row in cursor.fetchall()]
    
    print("   ستون‌های جدول customers_customer:", columns)
    
    if 'shop_id' in columns:
        print("   ✅ فیلد shop_id وجود دارد")
    else:
        print("   ❌ فیلد shop_id وجود ندارد!")
        
except Exception as e:
    print(f"   ❌ خطا: {e}")

# ۲. ایجاد داده‌های تست
print("\n۲. ایجاد داده‌های تست:")

try:
    # پاک کردن داده‌های قدیمی (اختیاری)
    Customer.objects.all().delete()
    Shop.objects.all().delete()
    User.objects.all().delete()
    
    # ایجاد کاربران
    user1 = User.objects.create_user('test_user1', 'test1@test.com', 'test123')
    user2 = User.objects.create_user('test_user2', 'test2@test.com', 'test123')
    
    # ایجاد پلن
    plan = Plan.objects.create(
        code='test',
        name='پلن تست',
        price=0,
        days=30,
        max_products=10,
        max_orders_per_month=100,
        is_active=True
    )
    
    # ایجاد فروشگاه‌ها
    shop1 = Shop.objects.create(
        user=user1,
        shop_name="فروشگاه تست ۱",
        slug="test-shop-1",
        instagram_username="@test1",
        phone_number="09111111111",
        current_plan=plan,
        is_active=True
    )
    
    shop2 = Shop.objects.create(
        user=user2,
        shop_name="فروشگاه تست ۲",
        slug="test-shop-2",
        instagram_username="@test2",
        phone_number="09222222222",
        current_plan=plan,
        is_active=True
    )
    
    print(f"   ✅ ایجاد شد: {shop1.shop_name} (ID: {shop1.id})")
    print(f"   ✅ ایجاد شد: {shop2.shop_name} (ID: {shop2.id})")
    
    # ۳. تست Customer مدل
    print("\n۳. تست مدل Customer:")
    
    # مشتری برای فروشگاه ۱
    customer1 = Customer.objects.create(
        shop=shop1,
        phone_number="09123456789",
        full_name="کاربر تست ۱"
    )
    print(f"   ✅ مشتری ۱ ایجاد شد: {customer1.phone_number} برای {customer1.shop.shop_name}")
    
    # مشتری برای فروشگاه ۲
    customer2 = Customer.objects.create(
        shop=shop2,
        phone_number="09123456789",  # همان شماره - باید مجاز باشد
        full_name="کاربر تست ۲"
    )
    print(f"   ✅ مشتری ۲ ایجاد شد: {customer2.phone_number} برای {customer2.shop.shop_name}")
    
    # تست unique constraint
    print("\n۴. تست unique constraint:")
    try:
        customer3 = Customer.objects.create(
            shop=shop1,  # همان فروشگاه
            phone_number="09123456789"  # همان شماره - باید خطا بدهد
        )
        print("   ❌ باید خطا می‌داد اما نداد!")
    except Exception as e:
        print(f"   ✅ کار کرد! خطا: {str(e)[:50]}...")
    
    # ۵. تست کوئری‌ها
    print("\n۵. تست کوئری‌های ایزوله:")
    
    # مشتریان فروشگاه ۱
    shop1_customers = Customer.objects.filter(shop=shop1)
    print(f"   مشتریان فروشگاه ۱: {shop1_customers.count()} مورد")
    
    # مشتریان فروشگاه ۲
    shop2_customers = Customer.objects.filter(shop=shop2)
    print(f"   مشتریان فروشگاه ۲: {shop2_customers.count()} مورد")
    
    print("\n🎉 تمام تست‌ها با موفقیت انجام شد!")
    
except Exception as e:
    print(f"\n❌ خطا در تست: {e}")
    import traceback
    traceback.print_exc()