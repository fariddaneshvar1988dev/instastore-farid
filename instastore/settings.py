"""
Django settings for instastore project.
Corrected and Optimized.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# در محیط واقعی (Production) حتما این کلید را از متغیرهای محیطی بخوانید
SECRET_KEY = 'django-insecure-*5i11fm+znb48@%q&^@a#+^dbt(h5kllya00ny^%wrl81xnxec'

# SECURITY WARNING: don't run with debug turned on in production!
# برای دیپلوی نهایی مقدار زیر را False کنید
DEBUG = True

# تغییر مهم: اضافه کردن '*' برای دسترسی از همه آدرس‌ها (برای محیط توسعه)
ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # کتابخانه کمکی برای نمایش خوانای اعداد (سه رقم سه رقم)
    'django.contrib.humanize', 
    'rest_framework',
    'shops',
    'customers',
    'orders',
    'products',
    'django_filters',
    'drf_yasg',
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
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'  # این خط برای دسترسی به فایل‌های مدیا ضروری است

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# مسیر هدایت پس از ورود موفق
LOGIN_REDIRECT_URL = 'seller-dashboard'
# مسیر هدایت پس از خروج
LOGOUT_REDIRECT_URL = 'home'
# آدرس صفحه لاگین (برای دکوریتور @login_required)
LOGIN_URL = 'login'



# instastore/settings.py

# ... (بقیه کدها)

# Logging Configuration
# instastore/settings.py



# ... (سایر تنظیمات)

# تنظیمات پیشرفته لاگینگ
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S'
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
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
        # لاگر اختصاصی برای اپلیکیشن‌های خودمان
        'instastore': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}