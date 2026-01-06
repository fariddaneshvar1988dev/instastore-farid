import logging
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
from shops.decorators import shop_required, shop_optional  # وارد کردن decoratorهای جدید
from products.models import Product, Category, ProductVariant, ProductImage
from orders.models import Order, OrderItem
from customers.models import Customer  # وارد کردن مدل اصلاح شده
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
        """پردازش فرم جستجوی سفارش - با در نظر گرفتن shop"""
        order_number = request.POST.get('order_number', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        if not order_number or not phone:
            return render(request, self.template_name, {
                'error': 'لطفا شماره سفارش و شماره موبایل را وارد کنید.'
            })

        try:
            # اگر کاربر در یک فروشگاه خاص است، فقط سفارشات آن فروشگاه را جستجو کن
            if hasattr(request, 'shop') and request.shop:
                order = Order.objects.get(
                    order_number__iexact=order_number,
                    phone_number=phone,
                    shop=request.shop  # 🔥 فیلتر مهم
                )
            else:
                # جستجوی عمومی (با ریسک کمتر)
                order = Order.objects.get(
                    order_number__iexact=order_number,
                    phone_number=phone
                )
            
            return render(request, self.template_name, {'order': order})
            
        except Order.DoesNotExist:
            return render(request, self.template_name, {
                'error': 'سفارشی با این مشخصات یافت نشد. لطفا اطلاعات را بررسی کنید.'
            })

class HomeView(TemplateView):
    template_name = 'frontend/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # اگر کاربر در یک فروشگاه خاص است، فقط محصولات آن فروشگاه را نشان بده
        if hasattr(self.request, 'shop') and self.request.shop:
            shop = self.request.shop
            products = Product.objects.filter(
                shop=shop,  # 🔥 فیلتر مهم
                is_active=True
            ).annotate(
                db_stock=Coalesce(Sum('variants__stock'), 0)
            ).order_by('-created_at')
            
            context['shop'] = shop
        else:
            # یا محصولات همه فروشگاه‌های فعال را نشان بده
            products = Product.objects.filter(
                shop__is_active=True,
                is_active=True
            ).annotate(
                db_stock=Coalesce(Sum('variants__stock'), 0)
            ).order_by('-created_at')
        
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
# 2. مدیریت سبد خرید - اصلاح شده برای ایزولاسیون
# ==========================================================

@require_POST
def add_to_cart(request, product_id):
    # ابتدا محصول را پیدا کن
    product = get_object_or_404(Product, id=product_id)
    
    # بررسی اینکه آیا کاربر در فروشگاه صحیح است
    if hasattr(request, 'shop') and request.shop:
        if product.shop_id != request.shop.id:
            return JsonResponse({'error': 'این محصول متعلق به این فروشگاه نیست.'}, status=400)
        shop = request.shop
    else:
        # اگر shop در request نیست، از محصول بگیر
        shop = product.shop
        # shop را در request ست کن برای consistency
        request.shop = shop
    
    # ایجاد cart با shop صحیح
    cart = Cart(request, shop=shop)
    
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

    try:
        cart.add(product=product, variant=variant, quantity=quantity)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

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
    
    # بررسی ایزولاسیون
    if hasattr(request, 'shop') and request.shop and shop.id != request.shop.id:
        return JsonResponse({'error': 'دسترسی غیرمجاز'}, status=403)
    
    cart = Cart(request, shop=shop)
    cart.remove(item_key)
    
    return render(request, 'partials/cart_sidebar.html', {
        'cart': cart,
        'shop': shop,
        'shop_slug': shop.slug
    })

def get_cart_component(request):
    # اگر shop در request است، از آن استفاده کن
    if hasattr(request, 'shop') and request.shop:
        shop = request.shop
    else:
        # یا از session بگیر
        shop_slug = request.GET.get('shop_slug')
        if shop_slug:
            shop = Shop.objects.filter(slug=shop_slug).first()
        else:
            shop = None
            
    cart = Cart(request, shop=shop) if shop else None
    return render(request, 'partials/cart_badge.html', {'cart': cart})

def get_cart_sidebar(request):
    shop_slug = request.GET.get('shop_slug')
    if not shop_slug:
        return JsonResponse({'error': 'فروشگاه مشخص نیست'}, status=400)
    
    shop = get_object_or_404(Shop, slug=shop_slug)
    cart = Cart(request, shop=shop)
    return render(request, 'partials/cart_sidebar.html', {
        'cart': cart,
        'shop': shop,
        'shop_slug': shop.slug
    })

# ==========================================================
# 3. فروشگاه و محصول - با decoratorهای ایزولاسیون
# ==========================================================

@method_decorator(shop_required, name='dispatch')
class ShopStoreView(TemplateView):
    template_name = 'frontend/shop_store.html'

    def get_context_data(self, **kwargs):
        # shop از طریق decorator و middleware در request.shop ست شده
        shop = self.request.shop
        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        
        # فقط محصولات این فروشگاه
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

@method_decorator(shop_required, name='dispatch')
class ProductDetailView(TemplateView):
    template_name = 'frontend/product_detail.html'

    def get_context_data(self, **kwargs):
        shop = self.request.shop  # از decorator می‌آید
        product_id = kwargs.get('product_id')
        
        # فقط محصولات این فروشگاه
        product = get_object_or_404(
            Product, 
            id=product_id, 
            shop=shop,  # 🔥 فیلتر مهم
            is_active=True
        )

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
            'id': v.id, 
            'color': v.color, 
            'size': v.size, 
            'stock': v.stock, 
            'price_adj': float(v.price_adjustment)
        } for v in variants]
        
        context['variants_json'] = variants_data
        return context

@method_decorator(shop_required, name='dispatch')
class CheckoutView(View):
    """نمایش صفحه تسویه حساب"""
    
    def get(self, request, shop_slug):
        shop = request.shop  # از decorator می‌آید
        cart = Cart(request, shop=shop)
        
        if cart.get_total_items() == 0:
            messages.warning(request, "سبد خرید شما خالی است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        cart_items_data = []
        for item in cart:
            variant = item['variant']
            
            # بررسی مالکیت محصول
            if variant.product.shop_id != shop.id:
                messages.error(request, "خطا در سبد خرید: محصول متعلق به این فروشگاه نیست.")
                return redirect('frontend:shop-store', shop_slug=shop.slug)
            
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
    
    def post(self, request, shop_slug):
        """ثبت سفارش"""
        shop = request.shop
        cart = Cart(request, shop=shop)
        
        if cart.get_total_items() == 0:
            return JsonResponse({'error': 'سبد خرید خالی است'}, status=400)
        
        # دریافت اطلاعات مشتری
        phone = request.POST.get('phone')
        full_name = request.POST.get('full_name')
        address = request.POST.get('address')
        
        if not all([phone, full_name, address]):
            return JsonResponse({'error': 'لطفا تمام اطلاعات را وارد کنید'}, status=400)
        
        # ایجاد یا دریافت مشتری برای این فروشگاه
        customer, created = Customer.get_or_create_for_shop(
            shop=shop,
            phone_number=phone,
            full_name=full_name,
            default_address=address
        )
        
        try:
            # ایجاد سفارش
            order = Order.objects.create(
                shop=shop,
                phone_number=phone,
                full_name=full_name,
                address=address,
                total_price=cart.get_total_price(),
                status='pending'
            )
            
            # ایجاد آیتم‌های سفارش
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    variant=item['variant'],
                    price=item['price'],
                    quantity=item['quantity']
                )
            
            # خالی کردن سبد خرید
            cart.clear()
            
            return JsonResponse({
                'success': True,
                'order_id': order.order_number,
                'redirect_url': f'/order/success/{order.order_number}/'
            })
            
        except Exception as e:
            logger.error(f"خطا در ثبت سفارش: {e}")
            return JsonResponse({'error': 'خطا در ثبت سفارش'}, status=500)

def order_success_view(request, order_id):
    """صفحه موفقیت سفارش"""
    order = get_object_or_404(Order, order_number=order_id)
    
    # بررسی دسترسی: فقط مشتری یا صاحب فروشگاه می‌تواند ببیند
    can_view = False
    
    if request.user.is_authenticated and hasattr(request.user, 'shop'):
        if order.shop == request.user.shop:
            can_view = True
    
    if order.phone_number and hasattr(request, 'session'):
        # می‌توانیم شماره تلفن را در session ذخیره کرده باشیم
        pass
    
    if not can_view and request.method == 'GET':
        # برای GET requests، کمی سخت‌گیرانه‌تر
        pass
    
    return render(request, 'frontend/order_success.html', {'order': order})

# ==========================================================
# 4. پنل فروشنده - با بررسی مالکیت
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
        # فقط محصولات متعلق به فروشگاه کاربر
        return Product.objects.filter(shop=self.request.user.shop)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.user.shop
        return kwargs

    def form_valid(self, form):
        self.object = form.save()
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
            'paid': Order.objects.filter(shop=shop, status='paid').count(),
            'processing': Order.objects.filter(shop=shop, status='processing').count(),
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
        # فقط سفارشات متعلق به فروشگاه کاربر
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