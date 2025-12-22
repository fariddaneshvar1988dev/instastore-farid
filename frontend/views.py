from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from shops.models import Shop
from products.models import Product, Category

# ========== صفحات اصلی ==========

class HomeView(TemplateView):
    """صفحه اصلی - جستجوی فروشگاه"""
    template_name = 'frontend/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # فروشگاه‌های فعال برای نمایش
        context['featured_shops'] = Shop.objects.filter(is_active=True)[:6]
        return context


class ShopStoreView(TemplateView):
    """صفحه فروشگاه - محصولات"""
    template_name = 'frontend/shop_store.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop_slug = kwargs.get('shop_slug')
        
        # پیدا کردن فروشگاه
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        context['shop'] = shop
        
        # دسته‌بندی‌های فروشگاه
        categories = Category.objects.filter(
            products__shop=shop,
            products__is_available=True
        ).distinct()
        context['categories'] = categories
        
        # محصولات
        products = Product.objects.filter(
            shop=shop,
            is_available=True
        ).select_related('category')
        
        # اعمال فیلترها
        category_id = self.request.GET.get('category')
        if category_id:
            products = products.filter(category_id=category_id)
        
        search_query = self.request.GET.get('q')
        if search_query:
            products = products.filter(name__icontains=search_query)
        
        context['products'] = products[:24]
        return context


class ProductDetailView(TemplateView):
    """صفحه جزئیات محصول"""
    template_name = 'frontend/product_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop_slug = kwargs.get('shop_slug')
        product_id = kwargs.get('product_id')
        
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        product = get_object_or_404(Product, id=product_id, shop=shop, is_available=True)
        
        context['shop'] = shop
        context['product'] = product
        context['related_products'] = Product.objects.filter(
            shop=shop,
            category=product.category,
            is_available=True
        ).exclude(id=product.id)[:4]
        
        return context


# ========== API‌های HTMX ==========

@require_http_methods(["GET"])
def load_more_products(request, shop_slug):
    """لود محصولات بیشتر"""
    shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
    
    offset = int(request.GET.get('offset', 0))
    limit = 12
    
    products = Product.objects.filter(
        shop=shop,
        is_available=True
    )[offset:offset + limit]
    
    if not products.exists():
        return JsonResponse({'has_more': False, 'html': ''})
    
    html = ''
    for product in products:
        html += f'''
        <div class="col-md-4 col-lg-3 mb-4">
            <div class="card product-card h-100">
                <div style="height: 200px; overflow: hidden;">
                    <img src="{product.images[0] if product.images else '/static/no-image.jpg'}" 
                         class="card-img-top" 
                         style="height: 100%; width: 100%; object-fit: cover;"
                         alt="{product.name}">
                </div>
                <div class="card-body d-flex flex-column">
                    <h6 class="card-title">{product.name[:50]}</h6>
                    <p class="card-text text-muted small mb-2" style="flex-grow: 1;">
                        {product.description[:80]}...
                    </p>
                    <div class="mt-auto">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="fw-bold text-success">
                                {int(product.get_price_in_toman()):,} تومان
                            </span>
                            <button class="btn btn-sm btn-primary">
                                <i class="bi bi-cart-plus"></i>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
    
    return JsonResponse({'has_more': products.count() == limit, 'html': html})


@require_http_methods(["GET"])
def search_products(request, shop_slug):
    """جستجوی محصولات"""
    shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
    
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        products = Product.objects.filter(
            shop=shop,
            is_available=True
        )[:12]
    else:
        products = Product.objects.filter(
            shop=shop,
            is_available=True,
            name__icontains=query
        )[:24]
    
    html = ''
    for product in products:
        html += f'''
        <div class="col-md-4 col-lg-3 mb-4">
            <div class="card product-card h-100">
                <div style="height: 200px; overflow: hidden;">
                    <img src="{product.images[0] if product.images else '/static/no-image.jpg'}" 
                         class="card-img-top" 
                         style="height: 100%; width: 100%; object-fit: cover;"
                         alt="{product.name}">
                </div>
                <div class="card-body d-flex flex-column">
                    <h6 class="card-title">{product.name[:50]}</h6>
                    <div class="mt-auto">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="fw-bold text-success">
                                {int(product.get_price_in_toman()):,} تومان
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        '''
    
    return JsonResponse({'html': html})


# ========== صفحات ساده ==========

def register_page(request):
    """صفحه ثبت‌نام"""
    return render(request, 'frontend/register.html')


def about_page(request):
    """صفحه درباره ما"""
    return render(request, 'frontend/about.html')


def contact_page(request):
    """صفحه تماس با ما"""
    return render(request, 'frontend/contact.html')



# تابع کمکی برای تشخیص نوع کاربر
def get_user_cart(request):
    """
    تشخیص نوع کاربر و برگرداندن سبد خرید مناسب
    Returns: (cart_type, cart_object)
    - ('guest', Cart) برای کاربران مهمان
    - ('customer', CustomerCart) برای مشتریان ثبت‌نام‌کرده
    - ('seller', None) برای صاحبان پیج
    """
    # اگر کاربر فروشنده است
    if hasattr(request.user, 'shop'):
        return 'seller', None
    
    # اگر کاربر مشتری ثبت‌نام‌کرده است
    if request.user.is_authenticated and hasattr(request.user, 'customer_profile'):
        customer = request.user.customer_profile
        cart, created = CustomerCart.objects.get_or_create(customer=customer)
        return 'customer', cart
    
    # کاربر مهمان
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    
    cart, created = Cart.objects.get_or_create(session_key=session_key)
    request.session['cart_id'] = cart.id
    return 'guest', cart

# اصلاح تابع add_to_cart
@require_http_methods(["POST"])
def add_to_cart(request, product_id):
    """افزودن محصول به سبد خرید (برای مشتریان)"""
    # اگر کاربر فروشنده است، اجازه خرید ندهد
    if hasattr(request.user, 'shop'):
        return JsonResponse({
            'success': False,
            'message': 'فروشندگان نمی‌توانند خرید کنند!'
        }, status=403)
    
    try:
        product = Product.objects.get(id=product_id, is_available=True, stock__gt=0)
        
        # تشخیص نوع کاربر و گرفتن سبد خرید مناسب
        cart_type, cart = get_user_cart(request)
        
        if cart_type == 'seller':
            return JsonResponse({
                'success': False,
                'message': 'فروشندگان نمی‌توانند خرید کنند!'
            }, status=403)
        
        # افزودن محصول به سبد
        cart.add_item(
            product_id=product.id,
            product_name=product.name,
            price=product.price,
            quantity=1,
            image=product.images[0] if product.images else None
        )
        
        return JsonResponse({
            'success': True,
            'message': 'محصول به سبد خرید اضافه شد',
            'cart_total': cart.get_total_items(),
            'cart_type': cart_type
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'محصول یافت نشد یا موجودی ندارد'
        }, status=404)
    


from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# ========== پنل مدیریت صاحب پیج ==========

@method_decorator(login_required, name='dispatch')
class SellerDashboardView(TemplateView):
    """پنل مدیریت صاحب پیج"""
    template_name = 'frontend/seller_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # فقط صاحبان پیج می‌توانند وارد شوند
        if not hasattr(request.user, 'shop'):
            from django.shortcuts import redirect
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        
        # آمار فروشگاه
        from orders.models import Order
        from products.models import Product
        
        total_orders = Order.objects.filter(shop=shop).count()
        pending_orders = Order.objects.filter(shop=shop, status='pending').count()
        total_products = Product.objects.filter(shop=shop).count()
        low_stock_products = Product.objects.filter(shop=shop, stock__lt=5).count()
        
        context.update({
            'shop': shop,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_products': total_products,
            'low_stock_products': low_stock_products,
            'recent_orders': Order.objects.filter(shop=shop).order_by('-created_at')[:5],
            'low_stock_items': Product.objects.filter(shop=shop, stock__lt=5)[:5],
        })
        
        return context

# ========== صفحات مدیریت محصولات ==========


@method_decorator(login_required, name='dispatch')
class SellerProductsView(TemplateView):
    template_name = 'frontend/seller_products.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'shop'):
            from django.shortcuts import redirect
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        
        # گرفتن محصولات
        products = Product.objects.filter(shop=shop)
        
        # محاسبه آمار
        context['available_count'] = products.filter(is_available=True).count()
        context['out_of_stock_count'] = products.filter(stock=0).count()
        context['products'] = products
        context['shop'] = shop
        context['categories'] = Category.objects.filter(products__shop=shop).distinct()
        
        return context

@method_decorator(login_required, name='dispatch')
class SellerOrdersView(TemplateView):
    """مدیریت سفارشات صاحب پیج"""
    template_name = 'frontend/seller_orders.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'shop'):
            return redirect('/')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        
        status_filter = self.request.GET.get('status', 'all')
        orders = Order.objects.filter(shop=shop)
        
        if status_filter != 'all':
            orders = orders.filter(status=status_filter)
        
        context.update({
            'shop': shop,
            'orders': orders.order_by('-created_at'),
            'status_filter': status_filter,
            'order_stats': {
                'all': Order.objects.filter(shop=shop).count(),
                'pending': Order.objects.filter(shop=shop, status='pending').count(),
                'confirmed': Order.objects.filter(shop=shop, status='confirmed').count(),
                'shipped': Order.objects.filter(shop=shop, status='shipped').count(),
                'delivered': Order.objects.filter(shop=shop, status='delivered').count(),
            }
        })
        
        return context