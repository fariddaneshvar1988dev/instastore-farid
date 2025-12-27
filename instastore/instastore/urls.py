from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # مسیر اصلی سایت به اپلیکیشن frontend متصل می‌شود
    path('', include('frontend.urls')),
    
    # سایر اپلیکیشن‌ها
    path('shops/', include('shops.urls')),
    path('products/', include('products.urls')),
    path('orders/', include('orders.urls')),
    path('customers/', include('customers.urls')),
]

# تنظیمات برای نمایش فایل‌های مدیا (تصاویر) در حالت دیباگ
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)