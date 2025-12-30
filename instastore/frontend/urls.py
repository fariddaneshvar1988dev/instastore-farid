from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # ---- صفحات عمومی ----
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
    path('register/', views.SellerRegisterView.as_view(), name='register-page'),
    path('login/', views.user_login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('order/success/<str:order_id>/', views.order_success_view, name='order-success'),
    # ---- پنل فروشنده ----
    path('seller/dashboard/', views.SellerDashboardView.as_view(), name='seller-dashboard'),
    path('seller/products/', views.SellerProductsView.as_view(), name='seller-products'),
    path('seller/products/add/', views.SellerProductCreateView.as_view(), name='seller-product-add'),
    path('seller/products/<int:pk>/edit/', views.SellerProductUpdateView.as_view(), name='seller-product-edit'),
    path('seller/products/<int:pk>/delete/', views.delete_product, name='seller-product-delete'),
    path('seller/orders/', views.SellerOrdersView.as_view(), name='seller-orders'),
    path('seller/orders/<int:pk>/', views.SellerOrderDetailView.as_view(), name='seller-order-detail'),
    path('seller/settings/', views.ShopSettingsView.as_view(), name='seller-settings'),
    path('seller/orders/<int:pk>/delete/', views.delete_order, name='seller-order-delete'),
    
    # مسیر صفحه موفقیت سفارش
    path('order/success/<str:order_id>/', views.order_success_view, name='order-success'),
    # ---- سبد خرید و اجزای کوچک (Components) ----
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add-to-cart'),
    path('cart/remove/<int:item_key>/', views.remove_from_cart, name='remove-from-cart'),
    path('cart/sidebar/', views.get_cart_sidebar, name='cart-sidebar'),
    path('cart/get-badge/', views.get_cart_component, name='cart-component'),

    # ---- فروشگاه و مشتری (اصلاح شده) ----
    path('track-order/', views.OrderTrackingView.as_view(), name='order-tracking'),
    
    # صفحه اصلی فروشگاه (مثلاً instavitrin.ir/shop/my-shop/)
    path('shop/<str:shop_slug>/', views.ShopStoreView.as_view(), name='shop-store'),
    
    # صفحه جزئیات محصول
    path('shop/<str:shop_slug>/product/<int:product_id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('track-order/', views.OrderTrackingView.as_view(), name='order-tracking'),
    # صفحه نهایی کردن خرید (Checkout)
    # این مسیر را با کلاس CheckoutView خودت هماهنگ کردیم
    path('shop/<str:shop_slug>/checkout/', views.CheckoutView.as_view(), name='checkout'),
]