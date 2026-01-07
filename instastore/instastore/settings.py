"""
Django settings for instastore project.
Optimized for Production Environment by DevOps Team.
"""

from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

# بارگذاری متغیرها از فایل .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# دامنه‌های مجاز را از env می‌خواند و تبدیل به لیست می‌کند
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

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
    'tailwind', # برای مدیریت تلویند
    'theme',    # نام اپلیکیشنی که استایل‌های ما در آن قرار می‌گیرد
    'django_browser_reload', # رفرش خودکار
    'django_htmx', # ابزارهای کمکی htmx
    
    # Local apps
    
    'customers.apps.CustomersConfig',
    'orders.apps.OrdersConfig',
    'products.apps.ProductsConfig',
    'frontend.apps.FrontendConfig',
    'shops.apps.ShopsConfig',
    'logs.apps.LogsConfig',
    'django_prometheus', # monitoring
]

# تنظیمات Swagger
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        },
        'Basic': {
            'type': 'basic'
        }
    },
    'USE_SESSION_AUTH': True,
    'LOGIN_URL': '/admin/login/',
    'LOGOUT_URL': '/admin/logout/',
    'JSON_EDITOR': True,
    'DEFAULT_MODEL_RENDERING': 'example',
    'DEEP_LINKING': True,
    'PERSIST_AUTH': True,
    'REFETCH_SCHEMA_ON_LOGOUT': True,
    'VALIDATOR_URL': None,
    'OPERATIONS_SORTER': 'alpha',
    'TAGS_SORTER': 'alpha',
    'DOC_EXPANSION': 'none',
    'SHOW_REQUEST_HEADERS': True,
    'SUPPORTED_SUBMIT_METHODS': ['get', 'post', 'put', 'delete', 'patch'],
    'DISPLAY_OPERATION_ID': False,
}

REDOC_SETTINGS = {
    'LAZY_RENDERING': False,
    'NATIVE_SCROLLBARS': False,
    'REQUIRED_PROPS_FIRST': True,
    'SORT_OPERATIONS_BY': 'method',
    'THEME': 'light',
}

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # Middlewareهای سفارشی
    'shops.middleware.ShopMiddleware',
    'django_htmx.middleware.HtmxMiddleware',
    'django_browser_reload.middleware.BrowserReloadMiddleware',
    
    'django_prometheus.middleware.PrometheusAfterMiddleware',
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
            # برای دیباگ بهتر
            'string_if_invalid': 'INVALID_TEMPLATE_VAR',
        },
    },
]

WSGI_APPLICATION = 'instastore.wsgi.application'

# Database
# اگر متغیرهای محیطی دیتابیس وجود داشت (در داکر)، از پستگرس استفاده کن
if os.environ.get('DB_NAME'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DB_NAME'),
            'USER': os.environ.get('DB_USER'),
            'PASSWORD': os.environ.get('DB_PASSWORD'),
            'HOST': os.environ.get('DB_HOST'),
            'PORT': os.environ.get('DB_PORT'),
        }
    }
else:
    # در محیط توسعه لوکال از SQLite استفاده کن
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
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'same-origin'

# برای محیط توسعه SSL غیرفعال باشد
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0

# اگر whitenoise نصب دارید، این خط را فعال کنید
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Logging - نسخه بهبود یافته برای دیباگ
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'instastore': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'drf_yasg': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': True,
        },
    },
}

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.openapi.AutoSchema',
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/day',
        'user': '1000/day'
    },
}

# Zarinpal payment gateway
ZARINPAL_MERCHANT_ID = os.environ.get('ZARINPAL_MERCHANT_ID', 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx')

# --- Tailwind Configuration ---
TAILWIND_APP_NAME = 'theme'

# تنظیمات NPM
NPM_BIN_PATH = r"C:/Program Files/nodejs/npm.cmd"

# --- Browser Reload Config ---
INTERNAL_IPS = [
    "127.0.0.1",
    "localhost",
]

# تنظیمات ایمیل (در صورت نیاز)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'webmaster@localhost')

# تنظیمات کش (در صورت نیاز)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# تنظیمات فایل آپلود
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB

# تنظیمات امنیتی اضافی برای production
if not DEBUG:
    # امنیت SSL
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # کوکی‌های امن
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # هدرهای امنیتی
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'same-origin'
    
    # Whitenoise برای static files
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# تنظیمات سفارشی پروژه
INSTASTORE_CONFIG = {
    'SITE_NAME': 'InstaStore',
    'SITE_DOMAIN': 'instavitrin.ir',
    'SUPPORT_EMAIL': 'support@instavitrin.ir',
    'SUPPORT_PHONE': '۰۲۱-۱۲۳۴۵۶۷۸',
    'DEFAULT_CURRENCY': 'ریال',
    'DEFAULT_LANGUAGE': 'fa',
    'MAX_PRODUCTS_PER_SHOP': 100,
    'MAX_IMAGES_PER_PRODUCT': 5,
    'ORDER_STATUSES': {
        'pending': 'در انتظار پرداخت',
        'paid': 'پرداخت شده',
        'processing': 'در حال پردازش',
        'shipped': 'ارسال شده',
        'delivered': 'تحویل داده شده',
        'canceled': 'لغو شده',
        'refunded': 'مرجوع شده',
    },
}

# تنظیمات CORS (در صورت نیاز API خارجی)
# CORS_ALLOWED_ORIGINS = [
#     "https://instavitrin.ir",
#     "https://www.instavitrin.ir",
#     "http://localhost:3000",
#     "http://127.0.0.1:3000",
# ]
# CORS_ALLOW_CREDENTIALS = True

# تنظیمات Celery (در صورت نیاز پردازش‌های پس‌زمینه)
# CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
# CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

print(f"✅ Django settings loaded successfully. DEBUG={DEBUG}")