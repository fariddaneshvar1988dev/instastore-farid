from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from frontend.views import get_cart_sidebar # ایمپورت تابع جدید
# ایمپورت صریح تمام ویوها (اضافه شدن remove_from_cart)
from frontend.views import (
    HomeView,
    ShopSettingsView,
    SellerRegisterView,
    SellerDashboardView,
    SellerProductsView,
    SellerProductCreateView,
    SellerProductUpdateView,
    SellerOrdersView,
    SellerOrderDetailView,
    ShopStoreView,
    ProductDetailView,
    CheckoutView,
    ProfileView,
    logout_view,
    about_page,
    contact_page,
    get_cart_component,
    cart_detail_view,
    load_more_products,
    search_products,
    add_to_cart,
    remove_from_cart,  # <--- این مورد جدید اضافه شد
    delete_product
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # --- صفحات عمومی ---
    path('', HomeView.as_view(), name='home'),
    path('about/', about_page, name='about'),
    path('contact/', contact_page, name='contact'),
    
    # --- احراز هویت ---
    path('login/', auth_views.LoginView.as_view(
        template_name='frontend/login.html', 
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', logout_view, name='logout'),
    path('register/', SellerRegisterView.as_view(), name='register-page'),
    
    # --- پنل فروشنده ---
    path('seller/dashboard/', SellerDashboardView.as_view(), name='seller-dashboard'),
    path('seller/settings/', ShopSettingsView.as_view(), name='seller-settings'),
    
    path('seller/products/', SellerProductsView.as_view(), name='seller-products'),
    path('seller/products/add/', SellerProductCreateView.as_view(), name='seller-product-create'),
    path('seller/products/<int:pk>/edit/', SellerProductUpdateView.as_view(), name='seller-product-edit'),
    path('seller/products/<int:pk>/delete/', delete_product, name='seller-product-delete'),
    
    path('seller/orders/', SellerOrdersView.as_view(), name='seller-orders'),
    path('seller/orders/<int:pk>/', SellerOrderDetailView.as_view(), name='seller-order-detail'),
    
    # --- فروشگاه سمت مشتری ---
    path('shop/<slug:shop_slug>/', ShopStoreView.as_view(), name='shop-store'),
    path('shop/<slug:shop_slug>/product/<int:product_id>/', ProductDetailView.as_view(), name='product-detail'),
    path('shop/<slug:shop_slug>/checkout/', CheckoutView.as_view(), name='checkout'),
    
    # --- سبد خرید و پروفایل ---
    path('cart/', cart_detail_view, name='cart-detail'),
    path('profile/', ProfileView.as_view(), name='user-profile'),
    
    # --- API ها ---
    path('cart/get/', get_cart_component, name='get-cart-component'),
    path('shop/<slug:shop_slug>/load-more/', load_more_products, name='load-more'),
    path('shop/<slug:shop_slug>/search/', search_products, name='search-products'),
    
    # عملیات سبد خرید
    path('api/cart/add/<int:product_id>/', add_to_cart, name='add-to-cart'),
    path('api/cart/sidebar/', get_cart_sidebar, name='get_cart_sidebar'), # این خط را اضافه کنید
    path('api/sellers/register/', SellerRegisterView.as_view(), name='api-register'),
    path('api/cart/remove/<str:item_key>/', remove_from_cart, name='remove-from-cart'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)