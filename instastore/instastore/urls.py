from django.contrib import admin
from django.urls import path, include ,re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# تنظیمات Swagger برای مستندات API
schema_view = get_schema_view(
   openapi.Info(
      title="InstaStore API",
      default_version='v1',
      description="مستندات کامل API فروشگاه اینستاگرامی",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@instastore.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

# الگوی URL اصلی
urlpatterns = [
    path('admin/', admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
    
    # اپلیکیشن‌های پروژه
    path('', include('frontend.urls')),
    
    # APIها
    path('api/shops/', include('shops.urls')),
    path('api/products/', include('products.urls')),
    path('api/orders/', include('orders.urls')),
    path('api/customers/', include('customers.urls')),
    
    # مسیرهای Swagger (مستندات)
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # monitoring
    path('prometheus/', include('django_prometheus.urls')),
]

# تنظیمات فایل‌های استاتیک و مدیا در محیط توسعه
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)