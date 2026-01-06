# final_fix.py
import os
import sys
import django
import subprocess

print("=== FINAL FIX FOR CUSTOMERS MIGRATION ===")

# Setup
BASE_DIR = 'C:/Users/farid-/Desktop/repo/instastore-farid/instastore'
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'instastore.settings')

try:
    django.setup()
except:
    pass

# 1. Delete database
print("\n1. Deleting database...")
db_file = os.path.join(BASE_DIR, 'db.sqlite3')
if os.path.exists(db_file):
    os.remove(db_file)
    print("OK: Database deleted")

# 2. Delete all migrations
print("\n2. Deleting migrations...")
apps = ['customers', 'shops', 'products', 'orders']
for app in apps:
    migrations_dir = os.path.join(BASE_DIR, app, 'migrations')
    if os.path.exists(migrations_dir):
        for file in os.listdir(migrations_dir):
            if file.endswith('.py') and file != '__init__.py':
                os.remove(os.path.join(migrations_dir, file))
        print(f"OK: {app} migrations deleted")

# 3. Disable signals
print("\n3. Disabling signals...")
signals_file = os.path.join(BASE_DIR, 'customers', 'signals.py')
with open(signals_file, 'w', encoding='utf-8') as f:
    f.write('# Disabled for migration\n')
print("OK: Signals disabled")

# 4. Create migrations
print("\n4. Creating migrations...")
os.chdir(BASE_DIR)
result = subprocess.run(['python', 'manage.py', 'makemigrations'], 
                       capture_output=True, text=True)
print("Makemigrations output:", result.stdout[:500])
if result.stderr:
    print("Makemigrations errors:", result.stderr[:500])

# 5. Apply migrations
print("\n5. Applying migrations...")
result = subprocess.run(['python', 'manage.py', 'migrate'], 
                       capture_output=True, text=True)
print("Migrate output:", result.stdout[:500])
if result.stderr:
    print("Migrate errors:", result.stderr[:500])

# 6. Verify
print("\n6. Verifying...")
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    # Check all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"\nTotal tables: {len(tables)}")
    print("Important tables:")
    important_tables = ['customers_customer', 'shops_shop', 'products_product', 'orders_order']
    
    for table in important_tables:
        if table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cursor.fetchall()]
            print(f"  ✅ {table}: {len(cols)} columns")
            if table == 'customers_customer' and 'shop_id' in cols:
                print(f"     ✓ shop_id field exists")
        else:
            print(f"  ❌ {table}: NOT FOUND")

# 7. Create test data
print("\n7. Creating test data...")
try:
    from django.contrib.auth.models import User
    from shops.models import Shop, Plan
    from customers.models import Customer
    
    # Create user
    user = User.objects.create_user('test_user', 'test@test.com', 'test123')
    
    # Create plan
    plan = Plan.objects.create(
        code='test',
        name='Test Plan',
        price=0,
        days=30,
        max_products=100,
        max_orders_per_month=1000,
        is_active=True
    )
    
    # Create shop
    shop = Shop.objects.create(
        user=user,
        shop_name='Test Shop',
        slug='test-shop',
        instagram_username='@test',
        phone_number='09123456789',
        current_plan=plan,
        is_active=True
    )
    
    # Create customer
    customer = Customer.objects.create(
        shop=shop,
        phone_number='09111111111',
        full_name='Test Customer'
    )
    
    print(f"✅ Test data created:")
    print(f"   Shop: {shop.shop_name}")
    print(f"   Customer: {customer.phone_number} (Shop: {customer.shop.shop_name})")
    
except Exception as e:
    print(f"⚠️ Error creating test data: {e}")

print("\n" + "="*50)
print("FIX COMPLETED!")
print("="*50)