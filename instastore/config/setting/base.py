"""
بخش تنظیمات مربوط به سیستم پلن‌ها و اشتراک‌ها
از فایل settings اصلی
"""

# تنظیمات سیستم پلن‌ها
PLAN_SETTINGS = {
    # پلن رایگان
    'FREE_PLAN': {
        'CODE': 'free',
        'DAYS': 5,  # 5 روز آزمایشی
        'MAX_PRODUCTS': 10,
        'MAX_ORDERS_PER_MONTH': 50,
        'PRICE': 0,
        'IS_DEFAULT': True,
    },
    
    # پلن پایه
    'BASIC_PLAN': {
        'CODE': 'basic',
        'DAYS': 30,
        'MAX_PRODUCTS': 100,
        'MAX_ORDERS_PER_MONTH': 500,
        'PRICE': 50000,  # 50,000 تومان
        'IS_DEFAULT': False,
    },
    
    # پلن حرفه‌ای
    'PRO_PLAN': {
        'CODE': 'pro',
        'DAYS': 30,
        'MAX_PRODUCTS': 500,
        'MAX_ORDERS_PER_MONTH': 5000,
        'PRICE': 150000,  # 150,000 تومان
        'IS_DEFAULT': False,
    },
    
    # پلن سازمانی
    'ENTERPRISE_PLAN': {
        'CODE': 'enterprise',
        'DAYS': 365,
        'MAX_PRODUCTS': 5000,
        'MAX_ORDERS_PER_MONTH': 50000,
        'PRICE': 500000,  # 500,000 تومان
        'IS_DEFAULT': False,
    },
}

# تنظیمات سیستم اشتراک
SUBSCRIPTION_SETTINGS = {
    # هشدارهای قبل از انقضا
    'EXPIRY_WARNINGS': [7, 3, 1],  # روزهای قبل از انقضا برای هشدار
    
    # رفتار پس از انقضا
    'AFTER_EXPIRY': {
        'ALLOW_SHOP_VIEW': True,  # آیا فروشگاه قابل مشاهده باشد؟
        'ALLOW_PRODUCT_VIEW': True,  # آیا محصولات قابل مشاهده باشند؟
        'BLOCK_NEW_ORDERS': True,  # آیا سفارش جدید مسدود شود؟
        'BLOCK_NEW_PRODUCTS': True,  # آیا محصول جدید مسدود شود؟
        'SHOW_EXPIRY_BANNER': True,  # آیا بنر انقضا نشان داده شود؟
    },
    
    # تمدید خودکار
    'AUTO_RENEWAL': {
        'ENABLED': False,  # آیا تمدید خودکار فعال باشد؟
        'DAYS_BEFORE_EXPIRY': 3,  # چند روز قبل از انقضا تمدید شود؟
        'RETRY_ATTEMPTS': 3,  # تعداد تلاش‌های پرداخت
        'RETRY_INTERVAL_DAYS': 2,  # فاصله بین تلاش‌ها
    },
    
    # محدودیت‌ها
    'LIMITS': {
        'MAX_PLANS_PER_SHOP': 1,  # حداکثر پلن فعال برای هر فروشگاه
        'PLAN_CHANGE_COOLDOWN_DAYS': 0,  # روزهای انتظار برای تغییر پلن
        'MAX_FREE_TRIALS_PER_USER': 1,  # حداکثر آزمایش رایگان برای هر کاربر
    },
}

# تنظیمات مالی
BILLING_SETTINGS = {
    # درگاه پرداخت
    'PAYMENT_GATEWAY': 'zarinpal',  # zarinpal, idpay, nextpay, etc.
    
    # زرین‌پال
    'ZARINPAL': {
        'MERCHANT_ID': env('ZARINPAL_MERCHANT_ID', ''),
        'SANDBOX': env('ZARINPAL_SANDBOX', True),
        'CALLBACK_URL': '/payment/verify/',
    },
    
    # مالیات
    'TAX': {
        'ENABLED': True,
        'PERCENTAGE': 9,  # 9 درصد ارزش افزوده
    },
    
    # کمیسیون پلتفرم
    'COMMISSION': {
        'ENABLED': True,
        'PERCENTAGE': 10,  # 10 درصد از هر تراکنش
        'MIN_AMOUNT': 1000,  # حداقل مبلغ کمیسیون
    },
    
    # صورتحساب
    'INVOICE': {
        'PREFIX': 'INV',
        'NUMBER_LENGTH': 8,
        'DUE_DAYS': 7,  # مهلت پرداخت
    },
}

# تنظیمات ادمین برای مدیریت پلن‌ها
ADMIN_PLAN_SETTINGS = {
    # دسترسی‌ها
    'PERMISSIONS': {
        'CAN_MANAGE_PLANS': True,  # آیا ادمین می‌تواند پلن‌ها را مدیریت کند؟
        'CAN_ASSIGN_PLANS': True,  # آیا ادمین می‌تواند پلن اختصاص دهد؟
        'CAN_EXTEND_SUBSCRIPTIONS': True,  # آیا ادمین می‌تواند اشتراک تمدید کند؟
        'CAN_VIEW_REVENUE': True,  # آیا ادمین می‌تواند درآمد را ببیند؟
    },
    
    # عملیات دسته‌ای
    'BATCH_OPERATIONS': {
        'MAX_SHOPS_PER_BATCH': 100,
        'ALLOWED_ACTIONS': ['extend', 'change_plan', 'activate', 'deactivate'],
    },
    
    # گزارش‌ها
    'REPORTS': {
        'REVENUE_REPORT_DAYS': 30,  # روزهای گزارش درآمد
        'TOP_PLANS_COUNT': 5,  # تعداد پلن‌های برتر
        'EXPORT_FORMATS': ['csv', 'excel', 'pdf'],
    },
}

# تنظیمات نمایش برای کاربران
USER_PLAN_SETTINGS = {
    # نمایش پلن‌ها
    'DISPLAY': {
        'SHOW_PRICES': True,
        'SHOW_COMPARISON': True,
        'HIGHLIGHT_POPULAR': True,
        'SHOW_SAVINGS': True,  # نمایش صرفه‌جویی برای پلن‌های سالانه
    },
    
    # هشدارها
    'ALERTS': {
        'SHOW_EXPIRY_ALERTS': True,
        'SHOW_LIMIT_ALERTS': True,
        'SHOW_UPGRADE_SUGGESTIONS': True,
    },
    
    # آزمایش رایگان
    'FREE_TRIAL': {
        'ENABLED': True,
        'DAYS': 5,
        'REQUIRE_CREDIT_CARD': False,
        'AUTO_CONVERT': False,  # آیا بعد از آزمایش به پلن پولی تبدیل شود؟
    },
}

# تنظیمات کارایی
PERFORMANCE_SETTINGS = {
    # کش
    'CACHE': {
        'PLANS_CACHE_TTL': 3600,  # 1 hour
        'SHOP_PLAN_CACHE_TTL': 300,  # 5 minutes
        'ENABLED': True,
    },
    
    # کوئری‌ها
    'QUERY_OPTIMIZATION': {
        'SELECT_RELATED': ['current_plan', 'user'],
        'PREFETCH_RELATED': ['products', 'orders'],
        'USE_INDEXES': True,
    },
    
    # background tasks
    'BACKGROUND_TASKS': {
        'CHECK_EXPIRIES_EVERY_HOURS': 1,
        'SEND_REMINDERS_EVERY_HOURS': 24,
        'CLEANUP_LOGS_EVERY_DAYS': 7,
    },
}

# تنظیمات توسعه و دیباگ
DEVELOPMENT_SETTINGS = {
    # تست
    'TESTING': {
        'AUTO_CREATE_TEST_PLANS': True,
        'CREATE_DEFAULT_PLANS': True,
        'TEST_SHOP_COUNT': 10,
    },
    
    # لاگ‌گیری
    'LOGGING': {
        'LOG_PLAN_CHANGES': True,
        'LOG_SUBSCRIPTION_EVENTS': True,
        'LOG_ADMIN_ACTIONS': True,
        'LOG_LEVEL': 'INFO',
    },
    
    # ویژگی‌های آزمایشی
    'EXPERIMENTAL_FEATURES': {
        'AI_PLAN_RECOMMENDATIONS': False,
        'PREDICTIVE_RENEWAL': False,
        'AUTOMATIC_PLAN_UPGRADES': False,
    },
}

# ادغام همه تنظیمات
PLATFORM_SETTINGS = {
    **PLAN_SETTINGS,
    'SUBSCRIPTION': SUBSCRIPTION_SETTINGS,
    'BILLING': BILLING_SETTINGS,
    'ADMIN_PLAN': ADMIN_PLAN_SETTINGS,
    'USER_PLAN': USER_PLAN_SETTINGS,
    'PERFORMANCE': PERFORMANCE_SETTINGS,
    'DEVELOPMENT': DEVELOPMENT_SETTINGS,
}

# تابع کمکی برای دسترسی به تنظیمات
def get_plan_settings(plan_code=None):
    """دریافت تنظیمات پلن"""
    if plan_code:
        for key, settings in PLAN_SETTINGS.items():
            if settings.get('CODE') == plan_code:
                return settings
    return PLAN_SETTINGS

def get_subscription_setting(setting_path):
    """دریافت تنظیمات اشتراک"""
    keys = setting_path.split('.')
    value = SUBSCRIPTION_SETTINGS
    for key in keys:
        value = value.get(key, {})
    return value

def is_feature_enabled(feature_name):
    """بررسی فعال بودن یک ویژگی"""
    experimental_features = DEVELOPMENT_SETTINGS.get('EXPERIMENTAL_FEATURES', {})
    return experimental_features.get(feature_name, False)