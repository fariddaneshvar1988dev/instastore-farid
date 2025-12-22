# 


from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from shops.views import RegisterSellerAPIView

# Import views from frontend app
from frontend.views import (
    HomeView, 
    ShopStoreView, 
    ProductDetailView,
    register_page, 
    about_page, 
    contact_page,
    load_more_products,
    search_products,
    
    SellerDashboardView, SellerProductsView, SellerOrdersView
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # Main pages
    path('', HomeView.as_view(), name='home'),
    path('register/', register_page, name='register-page'),
    path('about/', about_page, name='about'),
    path('contact/', contact_page, name='contact'),
    
    # Shop pages
    path('shop/<slug:shop_slug>/', ShopStoreView.as_view(), name='shop-store'),
    path('shop/<slug:shop_slug>/product/<int:product_id>/', 
         ProductDetailView.as_view(), name='product-detail'),
        
    
    # HTMX APIs
    path('shop/<slug:shop_slug>/load-more/', load_more_products, name='load-more'),
    path('shop/<slug:shop_slug>/search/', search_products, name='search-products'),
    
    path('api/sellers/register/', RegisterSellerAPIView.as_view(), name='api-register'),
    


    # ... URLهای قبلی
    
    # پنل مدیریت صاحب پیج
    path('seller/dashboard/', SellerDashboardView.as_view(), name='seller-dashboard'),
    path('seller/products/', SellerProductsView.as_view(), name='seller-products'),
    path('seller/orders/', SellerOrdersView.as_view(), name='seller-orders'),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)