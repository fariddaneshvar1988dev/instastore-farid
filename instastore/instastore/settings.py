"""
Django settings for instastore project.
Optimized for Production Environment.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# TODO: کلید را از متغیر محیطی بگیرید
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-*5i11fm+znb48@%q&^@a#+^dbt(h5kllya00ny^%wrl81xnxec')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True  

# دامنه‌های مجاز
ALLOWED_HOSTS = [
    'instavitrin.ir',
    'www.instavitrin.ir',
    '46.249.102.205',
    'localhost',
    '127.0.0.1',
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',  # نمایش خوانای اعداد
    
    # Third-party apps
    'rest_framework',
    'django_filters',
    'drf_yasg',
    # 'corsheaders',  # فعلاً غیرفعال کنید
    
    # Local apps
    'shops',
    'customers',
    'orders',
    'products',
    'frontend',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # اگر نصب کرده‌اید
    # 'corsheaders.middleware.CorsMiddleware',  # اگر نیاز به CORS دارید
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
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
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
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static_root')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
LOGIN_REDIRECT_URL = '/seller/dashboard/'
LOGOUT_REDIRECT_URL = '/'
LOGIN_URL = '/login/'

# Session & Cookies settings
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 هفته
SESSION_COOKIE_SECURE = False  # در توسعه False باشد
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_SAVE_EVERY_REQUEST = True

# CSRF settings
CSRF_COOKIE_SECURE = False  # در توسعه False باشد
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_TRUSTED_ORIGINS = [
    'https://instavitrin.ir',
    'https://www.instavitrin.ir',
]

# CORS settings (فعلاً غیرفعال)
# CORS_ALLOWED_ORIGINS = [
#     "https://instavitrin.ir",
#     "https://www.instavitrin.ir",
# ]
# CORS_ALLOW_CREDENTIALS = True

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# برای محیط توسعه SSL غیرفعال باشد
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# اگر whitenoise نصب ندارید، این خط را کامنت کنید
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging - نسخه ساده برای توسعه
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'instastore': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# DRF settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}

# Zarinpal payment gateway
ZARINPAL_MERCHANT_ID = os.environ.get('ZARINPAL_MERCHANT_ID', 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')



# ۴. معماری مشتریان (Customer vs User)

# شما یک مدل Customer اختصاصی دارید که به User جنگو متصل نیست.

# نکته: اگر قرار است در آینده لاگین با رمز عبور داشته باشید (که در settings.py احراز هویت DRF را دیدم)، باید راهی برای اتصال User (سیستم لاگین جنگو) به Customer (پروفایل فروشگاهی) پیدا کنیم. فعلاً برای شروع مشکلی نیست.