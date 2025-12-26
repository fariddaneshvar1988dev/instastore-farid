from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # ---- عمومی ----
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.about_page, name='about'),
    path('contact/', views.contact_page, name='contact'),
    path('register/', views.SellerRegisterView.as_view(), name='register-page'),
    path('login/', views.user_login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('track-order/', views.OrderTrackingView.as_view(), name='order-tracking'), # اضافه شده برای پیگیری

    # ---- فروشگاه (با پشتیبانی فارسی) ----
    path('shop/<str:shop_slug>/', views.ShopStoreView.as_view(), name='shop-store'),
    path('shop/<str:shop_slug>/checkout/', views.CheckoutView.as_view(), name='checkout'),

    # ---- پنل فروشنده ----
    path('seller/dashboard/', views.SellerDashboardView.as_view(), name='seller-dashboard'),
    path('seller/products/', views.SellerProductsView.as_view(), name='seller-products'),
    path('seller/products/add/', views.SellerProductCreateView.as_view(), name='seller-product-add'),
    path('seller/products/<int:pk>/edit/', views.SellerProductUpdateView.as_view(), name='seller-product-edit'),
    path('seller/products/<int:pk>/delete/', views.delete_product, name='seller-product-delete'),
    path('seller/orders/', views.SellerOrdersView.as_view(), name='seller-orders'),
    path('seller/orders/<int:pk>/', views.SellerOrderDetailView.as_view(), name='seller-order-detail'),
    path('seller/settings/', views.ShopSettingsView.as_view(), name='seller-settings'),

    # ---- مسیرهای اشتراک و پرداخت ----
    path('seller/plan/upgrade/', views.UpgradePlanView.as_view(), name='upgrade-plan'),
    path('seller/plan/pay/<int:plan_id>/', views.start_subscription_payment, name='start-payment'),
    path('seller/plan/callback/', views.payment_callback, name='payment-callback'),

    # ---- API های HTMX ----
    path('cart/get/', views.get_cart_component, name='cart-component'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add-to-cart'),
]