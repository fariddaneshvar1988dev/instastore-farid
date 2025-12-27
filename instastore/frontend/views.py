import logging
import json
from django.conf import settings
from django.db.models.functions import Coalesce
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView, View
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
from django.contrib.auth import login, logout, authenticate
from django.db import transaction
from django.utils import timezone

from shops.models import Shop
from products.models import Product, Category, ProductVariant
from orders.models import Order, OrderItem
from .forms import ProductForm, SellerRegisterForm, ShopSettingsForm
from .cart import Cart

logger = logging.getLogger('instastore')

# ==========================================================
# 1. صفحات عمومی (Public Pages)
# ==========================================================

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
# 2. مدیریت سبد خرید (Cart Logic)
# ==========================================================

@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # ایجاد سبد خرید اختصاصی برای این فروشگاه
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
    # ۱. پیدا کردن واریانت برای تشخیص فروشگاه
    variant = get_object_or_404(ProductVariant, id=item_key)
    shop = variant.product.shop
    
    # ۲. حذف از سبد خرید اختصاصی همان فروشگاه
    cart = Cart(request, shop_id=shop.id)
    cart.remove(item_key)
    
    # ۳. رندر کردن مجدد سایدبار برای HTMX
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
            
    # ایجاد شیء سبد خرید با توجه به فروشگاه فعلی
    cart = Cart(request, shop_id=shop_id)
    return render(request, 'partials/cart_badge.html', {'cart': cart})

def get_cart_sidebar(request):
    shop_slug = request.GET.get('shop_slug')
    shop = get_object_or_404(Shop, slug=shop_slug) # این خط مهم است
    cart = Cart(request, shop_id=shop.id)
    return render(request, 'partials/cart_sidebar.html', {
        'cart': cart,
        'shop': shop, # حتما ارسال شود
        'shop_slug': shop_slug
    })
    
    # پیدا کردن فروشگاه
    if shop_slug:
        shop = Shop.objects.filter(slug=shop_slug, is_active=True).first()
    
    # اگر فروشگاه پیدا شد، سبد مخصوص آن را لود کن، در غیر این صورت سبد پیش‌فرض
    if shop:
        cart = Cart(request, shop_id=shop.id)
    else:
        cart = Cart(request)

    return render(request, 'partials/cart_sidebar.html', {
        'cart': cart,
        'shop_slug': shop_slug,
        'shop': shop
    })
# ==========================================================
# 3. فروشگاه و محصول (Storefront)
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
        context['variants'] = product.variants.filter(stock__gt=0)
        
        variants_data = [{
            'id': v.id, 'color': v.color, 'size': v.size, 
            'stock': v.stock, 'price_adj': float(v.price_adjustment)
        } for v in context['variants']]
        context['variants_json'] = json.dumps(variants_data)
        return context

class CheckoutView(View):
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = Cart(request, shop_id=shop.id)
        
        if cart.get_total_items() == 0:
            messages.warning(request, "سبد خرید شما خالی است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        # چک کردن موجودی انبار قبل از نمایش فرم آدرس
        for item in cart:
            variant = item['variant']
            if variant.stock < item['quantity'] or not variant.product.is_active:
                messages.error(request, f"موجودی کالا یا وضعیت '{variant.product.name}' تغییر کرده است.")
                return redirect('frontend:shop-store', shop_slug=shop.slug)
            
        return render(request, 'frontend/checkout.html', {'shop': shop, 'cart': cart})

    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = Cart(request, shop_id=shop.id)
        
        if cart.get_total_items() == 0:
            messages.warning(request, "سبد خرید خالی است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        customer_phone = request.POST.get('customer_phone', '')
        if not customer_phone.startswith('09') or len(customer_phone) != 11:
            messages.error(request, "لطفاً یک شماره موبایل معتبر (مثل 09123456789) وارد کنید.")
            return render(request, 'frontend/checkout.html', {'shop': shop, 'cart': cart})

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    shop=shop,
                    customer_name=request.POST.get('customer_name'),
                    customer_phone=customer_phone,
                    shipping_address=request.POST.get('address'),
                    customer_notes=request.POST.get('note'),
                    subtotal=cart.get_total_price(),
                    total_amount=cart.get_total_price()
                )

                for item in cart:
                    variant = ProductVariant.objects.select_for_update().get(id=item['variant'].id)
                    if variant.stock < item['quantity']:
                        raise Exception(f"موجودی کالای '{variant.product.name}' در این لحظه به پایان رسید.")
                    
                    variant.stock -= item['quantity']
                    variant.save()
                    
                    OrderItem.objects.create(
                        order=order, variant=variant, product_name=variant.product.name,
                        quantity=item['quantity'], unit_price=item['price'], total_price=item['total_price']
                    )

                cart.clear()
                messages.success(request, f"سفارش شماره #{order.order_id} با موفقیت ثبت شد.")
                return redirect('frontend:shop-store', shop_slug=shop.slug)

        except Exception as e:
            logger.error(f"Checkout Error: {e}")
            messages.error(request, str(e))
            return redirect('frontend:checkout', shop_slug=shop.slug)

class OrderTrackingView(TemplateView):
    template_name = 'frontend/track_order.html'

# ==========================================================
# 4. پنل فروشنده (Seller Dashboard)
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

@method_decorator(login_required, name='dispatch')
class SellerProductCreateView(CreateView):
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
        
        fs = FileSystemStorage()
        if self.request.FILES.get('image1'):
            filename = fs.save(f"products/{self.request.FILES['image1'].name}", self.request.FILES['image1'])
            product.images = [fs.url(filename)]
            
        product.save()
        
        colors = self.request.POST.getlist('vars_color[]')
        sizes = self.request.POST.getlist('vars_size[]')
        stocks = self.request.POST.getlist('vars_stock[]')
        prices = self.request.POST.getlist('vars_price[]')
        
        if colors:
            for c, s, st, p in zip(colors, sizes, stocks, prices):
                ProductVariant.objects.create(
                    product=product, color=c, size=s, 
                    stock=int(st), price_adjustment=int(p) if p else 0
                )
        
        messages.success(self.request, "محصول با موفقیت ایجاد شد.")
        return redirect(self.success_url)

@method_decorator(login_required, name='dispatch')
class SellerProductUpdateView(UpdateView):
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

@require_http_methods(["POST", "DELETE"])
@login_required
def delete_product(request, pk):
    shop = request.user.shop
    product = get_object_or_404(Product, pk=pk, shop=shop)
    product.delete()
    return JsonResponse({'success': True})

@method_decorator(login_required, name='dispatch')
class SellerOrdersView(TemplateView):
    template_name = 'frontend/seller_orders.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        context['orders'] = Order.objects.filter(shop=shop).order_by('-created_at')
        context['shop'] = shop
        return context

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