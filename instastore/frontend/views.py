import logging
# import json  <-- نیازی نیست
from django.conf import settings
from django.db.models.functions import Coalesce
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView, View
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Sum
from django.contrib.auth import login, logout, authenticate
from django.utils import timezone

from shops.models import Shop
from products.models import Product, Category, ProductVariant, ProductImage
from orders.models import Order, OrderItem
from .forms import ProductForm, SellerRegisterForm, ShopSettingsForm
from .cart import Cart

logger = logging.getLogger('instastore')

# ==========================================================
# 1. صفحات عمومی و پیگیری سفارش
# ==========================================================

class OrderTrackingView(View):
    template_name = 'frontend/track_order.html'

    def get(self, request):
        """نمایش صفحه پیگیری سفارش"""
        return render(request, self.template_name)

    def post(self, request):
        """پردازش فرم جستجوی سفارش"""
        order_id = request.POST.get('order_id', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not order_id or not phone:
            return render(request, self.template_name, {
                'error': 'لطفا شماره سفارش و شماره موبایل را وارد کنید.'
            })

        try:
            # جستجو دقیق
            order = Order.objects.get(order_id__iexact=order_id, customer_phone=phone)
            return render(request, self.template_name, {'order': order})
            
        except Order.DoesNotExist:
            return render(request, self.template_name, {
                'error': 'سفارشی با این مشخصات یافت نشد. لطفا اطلاعات را بررسی کنید.'
            })

class HomeView(TemplateView):
    template_name = 'frontend/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.filter(is_active=True).annotate(
            db_stock=Coalesce(Sum('variants__stock'), 0)
        ).order_by('-created_at')

        if self.request.user.is_authenticated and hasattr(self.request.user, 'shop'):
            context['shop'] = self.request.user.shop

        context.update({
            'products': products[:12],
            'available_count': products.filter(db_stock__gt=0).count(),
        })
        return context

def about_page(request):
    return render(request, 'frontend/about.html')

def contact_page(request):
    return render(request, 'frontend/contact.html')

@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = 'frontend/profile.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shop'] = getattr(self.request.user, 'shop', None)
        return context

# ==========================================================
# 2. مدیریت سبد خرید
# ==========================================================

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = Cart(request, shop_id=product.shop.id)
    
    variant_id = request.POST.get('variant_id')
    quantity = int(request.POST.get('quantity', 1))
    
    if not variant_id:
        return JsonResponse({'error': 'لطفا رنگ و سایز را انتخاب کنید.'}, status=400)
    
    try:
        variant = ProductVariant.objects.get(id=variant_id, product=product)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'error': 'این محصول نامعتبر است.'}, status=404)

    if variant.stock < quantity:
        return JsonResponse({'error': 'موجودی انبار کافی نیست.'}, status=400)

    cart.add(product=product, variant=variant, quantity=quantity)

    return JsonResponse({
        'success': True,
        'message': 'به سبد خرید اضافه شد',
        'cart_count': cart.get_total_items(),
        'cart_total': float(cart.get_total_price())
    })

@require_POST
def remove_from_cart(request, item_key):
    try:
        variant = ProductVariant.objects.get(id=item_key)
        shop = variant.product.shop
    except ProductVariant.DoesNotExist:
        return JsonResponse({'error': 'محصول یافت نشد'}, status=404)
    
    cart = Cart(request, shop_id=shop.id)
    cart.remove(item_key)
    
    return render(request, 'partials/cart_sidebar.html', {
        'cart': cart,
        'shop': shop,
        'shop_slug': shop.slug
    })

def get_cart_component(request):
    shop_slug = request.GET.get('shop_slug')
    shop_id = None
    if shop_slug:
        shop = Shop.objects.filter(slug=shop_slug).first()
        if shop:
            shop_id = shop.id
            
    cart = Cart(request, shop_id=shop_id)
    return render(request, 'partials/cart_badge.html', {'cart': cart})

def get_cart_sidebar(request):
    shop_slug = request.GET.get('shop_slug')
    shop = get_object_or_404(Shop, slug=shop_slug)
    cart = Cart(request, shop_id=shop.id)
    return render(request, 'partials/cart_sidebar.html', {
        'cart': cart,
        'shop': shop,
        'shop_slug': shop.slug
    })

# ==========================================================
# 3. فروشگاه و محصول
# ==========================================================

class ShopStoreView(TemplateView):
    template_name = 'frontend/shop_store.html'

    def get_context_data(self, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        
        products = Product.objects.filter(shop=shop, is_active=True)
        category_slug = self.request.GET.get('category')
        if category_slug:
            products = products.filter(category__slug=category_slug)

        search_query = self.request.GET.get('q')
        if search_query:
            products = products.filter(name__icontains=search_query)

        context['products'] = products[:24]
        context['categories'] = Category.objects.filter(products__shop=shop).distinct()
        return context

class ProductDetailView(TemplateView):
    template_name = 'frontend/product_detail.html'

    def get_context_data(self, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        product_id = kwargs.get('product_id')
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        product = get_object_or_404(Product, id=product_id, shop=shop, is_active=True)

        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        context['product'] = product
        
        variants = product.variants.filter(stock__gt=0)
        context['variants'] = variants
        
        unique_colors = set(v.color for v in variants if v.color)
        unique_sizes = set(v.size for v in variants if v.size)
        context['unique_colors'] = sorted(list(unique_colors))
        context['unique_sizes'] = sorted(list(unique_sizes))
        
        variants_data = [{
            'id': v.id, 'color': v.color, 'size': v.size, 
            'stock': v.stock, 'price_adj': float(v.price_adjustment)
        } for v in variants]
        
        context['variants_json'] = variants_data
        return context

class CheckoutView(View):
    """نمایش صفحه تسویه حساب"""
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = Cart(request, shop_id=shop.id)
        
        if cart.get_total_items() == 0:
            messages.warning(request, "سبد خرید شما خالی است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        cart_items_data = []
        for item in cart:
            variant = item['variant']
            if variant.stock < item['quantity'] or not variant.product.is_active:
                messages.error(request, f"موجودی کالا یا وضعیت '{variant.product.name}' تغییر کرده است.")
                return redirect('frontend:shop-store', shop_slug=shop.slug)
            
            cart_items_data.append({
                "variant_id": variant.id,
                "quantity": item['quantity']
            })
            
        return render(request, 'frontend/checkout.html', {
            'shop': shop, 
            'cart': cart,
            'cart_items_json': cart_items_data  
        })

def order_success_view(request, order_id):
    """صفحه موفقیت سفارش برای مهمان و عضو"""
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, 'frontend/order_success.html', {'order': order})

# ==========================================================
# 4. پنل فروشنده
# ==========================================================

class SellerRegisterView(CreateView):
    template_name = 'frontend/register.html'
    form_class = SellerRegisterForm
    success_url = reverse_lazy('frontend:seller-dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'shop'):
            return redirect('frontend:seller-dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        shop = Shop.objects.create(
            user=user,
            shop_name=form.cleaned_data['shop_name'],
            slug=form.cleaned_data['shop_slug'],
            instagram_username=form.cleaned_data['instagram_username']
        )
        shop.plan_expires_at = timezone.now() + timezone.timedelta(days=30)
        shop.save()
        messages.success(self.request, "فروشگاه با موفقیت ساخته شد.")
        return redirect(self.success_url)

def user_login_view(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return redirect('/admin/')
        return redirect('frontend:seller-dashboard')
    
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
            if user.is_superuser:
                return redirect('/admin/')
            return redirect('frontend:seller-dashboard')
        messages.error(request, "نام کاربری یا رمز عبور اشتباه است.")
    return render(request, 'frontend/login.html')

def logout_view(request):
    logout(request)
    return redirect('frontend:home')

@method_decorator(login_required, name='dispatch')
class SellerDashboardView(TemplateView):
    template_name = 'frontend/seller_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'shop'):
            return redirect('frontend:register-page')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        context.update({
            'shop': shop,
            'total_products': Product.objects.filter(shop=shop).count(),
            'total_orders': Order.objects.filter(shop=shop).count(),
            'pending_orders': Order.objects.filter(shop=shop, status='pending').count()
        })
        return context

@method_decorator(login_required, name='dispatch')
class SellerProductsView(TemplateView):
    template_name = 'frontend/seller_products.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        products = Product.objects.filter(shop=shop).annotate(
            db_stock=Coalesce(Sum('variants__stock'), 0)
        ).order_by('-created_at')

        context.update({
            'products': products,
            'shop': shop,
            'available_count': products.filter(db_stock__gt=0).count(),
            'out_of_stock_count': products.filter(db_stock=0).count(),
        })
        return context

class SellerProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend/seller_product_form.html'
    success_url = reverse_lazy('frontend:seller-products')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.user.shop
        return kwargs

    def form_valid(self, form):
        product = form.save(commit=False)
        product.shop = self.request.user.shop
        product.save()
        
        for field_name in ['image1', 'image2', 'image3']:
            image_file = self.request.FILES.get(field_name)
            if image_file:
                ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    alt_text=product.name
                )
        
        colors = self.request.POST.getlist('vars_color[]')
        sizes = self.request.POST.getlist('vars_size[]')
        stocks = self.request.POST.getlist('vars_stock[]')
        prices = self.request.POST.getlist('vars_price[]')
        
        has_variant = False
        if colors:
            for c, s, st, p in zip(colors, sizes, stocks, prices):
                if st:
                    ProductVariant.objects.create(
                        product=product, 
                        color=c, 
                        size=s, 
                        stock=int(st), 
                        price_adjustment=int(p) if p else 0
                    )
                    has_variant = True
        
        if not has_variant:
            ProductVariant.objects.create(product=product, stock=10, price_adjustment=0)
        
        messages.success(self.request, "محصول با موفقیت ایجاد شد.")
        return redirect(self.success_url)

class SellerProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend/seller_product_form.html'
    success_url = reverse_lazy('frontend:seller-products')

    def get_queryset(self):
        return Product.objects.filter(shop=self.request.user.shop)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.user.shop
        return kwargs

    def form_valid(self, form):
        self.object = form.save()

        for field_name in ['image1', 'image2', 'image3']:
            image_file = self.request.FILES.get(field_name)
            if image_file:
                ProductImage.objects.create(
                    product=self.object,
                    image=image_file,
                    alt_text=self.object.name
                )
        
        messages.success(self.request, "محصول ویرایش شد.")
        return redirect(self.success_url)

@require_http_methods(["POST", "DELETE"])
@login_required
def delete_product(request, pk):
    shop = request.user.shop
    product = get_object_or_404(Product, pk=pk, shop=shop)
    product.is_active = False 
    product.save()
    return JsonResponse({'success': True, 'message': 'محصول بایگانی شد.'})

@method_decorator(login_required, name='dispatch')
class SellerOrdersView(TemplateView):
    template_name = 'frontend/seller_orders.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        
        status_filter = self.request.GET.get('status', 'all')
        orders = Order.objects.filter(shop=shop).order_by('-created_at')
        
        if status_filter != 'all':
            orders = orders.filter(status=status_filter)
            
        context['orders'] = orders
        context['shop'] = shop
        context['status_filter'] = status_filter
        
        context['order_stats'] = {
            'pending': Order.objects.filter(shop=shop, status='pending').count(),
            'confirmed': Order.objects.filter(shop=shop, status='confirmed').count(),
            'shipped': Order.objects.filter(shop=shop, status='shipped').count(),
            'delivered': Order.objects.filter(shop=shop, status='delivered').count(),
        }
        return context

@require_http_methods(["POST", "DELETE"])
@login_required
def delete_order(request, pk):
    shop = request.user.shop
    order = get_object_or_404(Order, pk=pk, shop=shop)
    try:
        order.delete()
        return JsonResponse({'success': True, 'message': 'سفارش با موفقیت حذف شد.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@method_decorator(login_required, name='dispatch')
class SellerOrderDetailView(DetailView):
    model = Order
    template_name = 'frontend/seller_order_detail.html'
    context_object_name = 'order'
    def get_queryset(self):
        return Order.objects.filter(shop=self.request.user.shop)

@method_decorator(login_required, name='dispatch')
class ShopSettingsView(UpdateView):
    model = Shop
    form_class = ShopSettingsForm
    template_name = 'frontend/seller_settings.html'
    success_url = reverse_lazy('frontend:seller-settings')
    def get_object(self):
        return self.request.user.shop
    def form_valid(self, form):
        messages.success(self.request, "تنظیمات با موفقیت ذخیره شد.")
        return super().form_valid(form)