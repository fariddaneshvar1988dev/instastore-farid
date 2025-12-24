from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from frontend import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- احراز هویت (Auth) ---
    # این خط قبلاً نبود و باعث ارور 404 می‌شد
    path('login/', auth_views.LoginView.as_view(template_name='frontend/login.html', redirect_authenticated_user=True), name='login'),
    
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.SellerRegisterView.as_view(), name='register-page'),
    
    # --- کامپوننت‌های HTMX ---
    path('cart/get/', views.get_cart_component, name='get-cart-component'),
    
    # --- صفحات عمومی ---
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
    
    # --- پنل فروشنده ---
    path('seller/dashboard/', views.SellerDashboardView.as_view(), name='seller-dashboard'),
    path('seller/products/', views.SellerProductsView.as_view(), name='seller-products'),
    path('seller/products/add/', views.SellerProductCreateView.as_view(), name='seller-product-create'),
    path('seller/products/<int:pk>/edit/', views.SellerProductUpdateView.as_view(), name='seller-product-edit'),
    path('seller/products/<int:pk>/delete/', views.delete_product, name='seller-product-delete'),
    path('seller/orders/', views.SellerOrdersView.as_view(), name='seller-orders'),
    path('seller/orders/<int:pk>/', views.SellerOrderDetailView.as_view(), name='seller-order-detail'),
    
    # --- فروشگاه سمت مشتری (Storefront) ---
    path('shop/<slug:shop_slug>/', views.ShopStoreView.as_view(), name='shop-store'),
    path('shop/<slug:shop_slug>/product/<int:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('shop/<slug:shop_slug>/checkout/', views.CheckoutView.as_view(), name='checkout'),
    
    
    # --- API ها ---
    path('shop/<slug:shop_slug>/load-more/', views.load_more_products, name='load-more'),
    path('shop/<slug:shop_slug>/search/', views.search_products, name='search-products'),
    path('api/cart/add/<int:product_id>/', views.add_to_cart, name='add-to-cart'),
    # مسیر ثبت‌نام API که در لاگ‌ها دیدیم
    path('api/sellers/register/', views.SellerRegisterView.as_view(), name='api-register'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)