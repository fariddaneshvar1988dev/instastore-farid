from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # اپلیکیشن اصلی فرانت‌اند (مسیرهای کاربر عادی و فروشنده)
    path('', include('frontend.urls')),

    # ---- اضافه کردن مسیرهای API (برای توسعه‌های آینده یا اپ موبایل) ----
    path('api/shops/', include('shops.urls')),
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/customers/', include('customers.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)