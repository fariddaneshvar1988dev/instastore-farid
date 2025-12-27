"""
Django settings for instastore project.
Corrected and Optimized for Local Development.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-*5i11fm+znb48@%q&^@a#+^dbt(h5kllya00ny^%wrl81xnxec'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# اجازه دسترسی از همه آدرس‌ها (برای محیط توسعه)
ALLOWED_HOSTS = ['*']


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # کتابخانه کمکی برای نمایش خوانای اعداد
    'django.contrib.humanize', 
    
    # Third-party apps
    'rest_framework',
    'django_filters',
    'drf_yasg',
    
    # Local apps
    'shops',
    'customers',
    'orders',
    'products',
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # میدل‌ور اختصاصی فروشگاه
    'shops.middleware.ShopMiddleware',
]

ROOT_URLCONF = 'instastore.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates',],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # کانتکست پروسسور سبد خرید
                'frontend.context_processors.cart_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'instastore.wsgi.application'


# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]


# Internationalization
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# تنظیمات فایل‌های آپلودی (Media)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- تنظیمات احراز هویت ---
# مسیر هدایت پس از ورود موفق
LOGIN_REDIRECT_URL = 'seller-dashboard'
# مسیر هدایت پس از خروج
LOGOUT_REDIRECT_URL = 'home'
# آدرس صفحه لاگین
LOGIN_URL = 'login'


# --- تنظیمات حیاتی برای رفع مشکل سبد خرید (Session & Cookies) ---
# این بخش باعث می‌شود سبد خرید روی لوکال‌هاست درست کار کند
SESSION_SAVE_EVERY_REQUEST = True  # ذخیره تغییرات سشن در هر درخواست
SESSION_COOKIE_SECURE = False      # غیرفعال کردن امنیت HTTPS برای لوکال
CSRF_COOKIE_SECURE = False         # غیرفعال کردن امنیت CSRF برای لوکال
SESSION_COOKIE_AGE = 1209600       # عمر سشن (۲ هفته)


# --- تنظیمات لاگینگ (Logging) ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'debug.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'standard',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'instastore': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}



# تنظیمات درگاه پرداخت
# این کد تست زرین‌پال است. برای نسخه واقعی باید کد اختصاصی خود را بگیرید
ZARINPAL_MERCHANT_ID = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
# --- این خطوط را حتما به آخر فایل settings.py اضافه کنید ---

# ۱. ذخیره سشن در هر بار درخواست (برای جلوگیری از پریدن سبد خرید)
SESSION_SAVE_EVERY_REQUEST = True

# ۲. تنظیمات کوکی برای کار روی لوکال هاست (بسیار مهم)
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True

# ۳. عمر سشن (مثلا ۲ هفته)
SESSION_COOKIE_AGE = 1209600 

# ۴. انجین سشن
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
