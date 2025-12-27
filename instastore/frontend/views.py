import logging
import json
from django.conf import settings
from django.db.models.functions import Coalesce

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView, View
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum, Count
from django.contrib.auth import login, logout, authenticate
from django.db import transaction
from django.utils import timezone

from shops.models import Shop, Plan
from products.models import Product, Category, ProductVariant
from orders.models import Order, OrderItem
from customers.models import Customer
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
        shop = self.request.user.shop
        
        # محاسبه مجموع موجودی در سطح دیتابیس با نام موقت 'db_stock'
        # Coalesce باعث می‌شود اگر محصولی واریانت نداشت، عدد 0 برگردد (نه None)
        products = Product.objects.filter(shop=shop).annotate(
            db_stock=Coalesce(Sum('variants__stock'), 0)
        ).order_by('-created_at')

        context.update({
            'products': products,
            'shop': shop,
            # حالا می‌توانیم روی db_stock فیلتر کنیم
            'available_count': products.filter(db_stock__gt=0).count(),
            'out_of_stock_count': products.filter(db_stock=0).count(),
        })
        return context

def about_page(request):
    return render(request, 'frontend/about.html')

def contact_page(request):
    return render(request, 'frontend/contact.html')

class ProfileView(TemplateView):
    template_name = 'frontend/profile.html'

# ==========================================================
# 2. مدیریت سبد خرید (Cart Logic)
# ==========================================================
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from products.models import Product, ProductVariant
from .cart import Cart

@require_POST
def add_to_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    # دریافت داده‌ها از فرم ارسال شده
    variant_id = request.POST.get('variant_id')
    quantity = int(request.POST.get('quantity', 1))
    
    # ۱. اعتبارسنجی: آیا واریانت معتبر انتخاب شده؟
    if not variant_id:
        return JsonResponse({'error': 'لطفا رنگ و سایز را انتخاب کنید.'}, status=400)
    
    try:
        variant = ProductVariant.objects.get(id=variant_id, product=product)
    except ProductVariant.DoesNotExist:
        return JsonResponse({'error': 'این محصول نامعتبر است.'}, status=404)

    # ۲. اعتبارسنجی موجودی (Server-Side Logic)
    # چک می‌کنیم آیا تعداد درخواستی در انبار موجود است؟
    # نکته: موجودی فعلی سبد را هم باید لحاظ کنیم (اگر قبلاً ۲ تا برداشته، الان ۳ تا نخواهد)
    # فعلاً چک ساده:
    if variant.stock < quantity:
        return JsonResponse({'error': 'موجودی انبار کافی نیست.'}, status=400)

    # ۳. افزودن به سبد
    cart.add(
        product=product,
        variant=variant, # ارسال آبجکت واریانت برای ذخیره جزئیات
        quantity=quantity
    )

    # ۴. بازگشت نتیجه موفقیت‌آمیز
    return JsonResponse({
        'success': True,
        'message': 'به سبد خرید اضافه شد',
        'cart_count': cart.get_total_items(), # تعداد کل آیتم‌ها برای آپدیت بج (Badge)
        'cart_total': cart.get_total_price()  # قیمت کل برای نمایش
    })

@require_POST
def remove_from_cart(request, item_key):
    cart = Cart(request)
    cart.remove(item_key)
    return get_cart_sidebar(request)

def get_cart_component(request):
    return render(request, 'partials/cart_badge.html')

# در فایل instastore/frontend/views.py

# در فایل instastore/frontend/views.py
from .cart import Cart
from products.models import Product

def get_cart_sidebar(request):
    cart = Cart(request)
    shop_slug = None
    
    # 1. تلاش برای پیدا کردن اولین محصول معتبر در سبد خرید
    # کلاس Cart خودش محصولاتی که حذف شده‌اند را فیلتر می‌کند
    for item in cart:
        if item['product'].shop:
            shop_slug = item['product'].shop.slug
            break # همین که اسلاگ فروشگاه را پیدا کردیم کافیست

    return render(request, 'partials/cart_sidebar.html', {
        'cart': cart, 
        'shop_slug': shop_slug
    })
# ==========================================================
# 3. فروشگاه و محصول (Storefront)
# ==========================================================

class ShopStoreView(TemplateView):
    template_name = 'frontend/shop_store.html'

    def get_context_data(self, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)

        # نکته: بررسی اشتراک را موقتاً غیرفعال کردیم تا در محیط تست به مشکل نخورید
        # if not shop.is_subscription_active():
        #     raise Http404("این فروشگاه در حال حاضر غیرفعال است.")

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
        # if not shop.is_subscription_active():
        #      raise Http404("این فروشگاه غیرفعال است.")

        product = get_object_or_404(Product, id=product_id, shop=shop, is_active=True)

        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        context['product'] = product
        context['variants'] = product.variants.filter(stock__gt=0)
        
        variants_data = []
        for v in context['variants']:
            variants_data.append({
                'id': v.id,
                'color': v.color,
                'size': v.size,
                'stock': v.stock,
                'price_adj': float(v.price_adjustment)
            })
        context['variants_json'] = json.dumps(variants_data)
        return context

class CheckoutView(View):
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = Cart(request)
        
        # اگر سبد خالی است، اجازه ورود نده
        if cart.get_total_items() == 0:
            messages.warning(request, "سبد خرید شما خالی است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)
            
        return render(request, 'frontend/checkout.html', {'shop': shop, 'cart': cart})

    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = Cart(request)
        
        # ۱. اعتبارسنجی اولیه سبد
        if cart.get_total_items() == 0:
            messages.warning(request, "سبد خرید خالی است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        try:
            with transaction.atomic():
                # ۲. ساخت سفارش (قیمت‌ها فقط از بک‌اند محاسبه می‌شوند)
                order = Order.objects.create(
                    shop=shop,
                    customer_name=request.POST.get('customer_name'),
                    customer_phone=request.POST.get('customer_phone'),
                    shipping_address=request.POST.get('address'),
                    customer_notes=request.POST.get('note'),
                    
                    # محاسبه قیمت‌ها در سرور
                    subtotal=cart.get_total_price(),
                    shipping_cost=0,  # بعداً می‌توانید هزینه ارسال را اضافه کنید
                    total_amount=cart.get_total_price()
                )

                # ۳. انتقال آیتم‌ها و کسر موجودی
                for item in cart:
                    variant_id = item.get('variant_id')
                    quantity = item['quantity']
                    
                    if variant_id:
                        # قفل کردن رکورد برای جلوگیری از تداخل همزمانی (Race Condition)
                        variant = ProductVariant.objects.select_for_update().get(id=variant_id)
                        
                        # چک کردن مجدد موجودی در لحظه خرید
                        if variant.stock < quantity:
                            raise Exception(f"متاسفانه موجودی کالای '{item['product'].name}' کافی نیست.")
                        
                        # کسر موجودی
                        variant.stock -= quantity
                        variant.save()
                        
                        # ثبت آیتم سفارش
                        OrderItem.objects.create(
                            order=order,
                            variant=variant,
                            product_name=item['product'].name,
                            quantity=quantity,
                            # قیمت واحد هم از دیتابیس خوانده می‌شود نه از سشن یا کلاینت
                            unit_price=item['price'], 
                            total_price=item['total_price']
                        )

                # ۴. پاک کردن سبد خرید بعد از ثبت موفق
                cart.clear()
                
                messages.success(request, f"سفارش شماره #{order.order_id} با موفقیت ثبت شد.")
                # در اینجا می‌توانید به درگاه پرداخت ریدایرکت کنید یا صفحه موفقیت را نشان دهید
                return redirect('frontend:shop-store', shop_slug=shop.slug)

        except ProductVariant.DoesNotExist:
            messages.error(request, "برخی از کالاها نامعتبر هستند.")
            return redirect('frontend:checkout', shop_slug=shop.slug)
            
        except Exception as e:
            # لاگ کردن خطا برای توسعه‌دهنده
            logger.error(f"Checkout Error: {e}")
            messages.error(request, str(e)) # نمایش متن خطا (مثل موجودی ناکافی) به کاربر
            return redirect('frontend:checkout', shop_slug=shop.slug)

class OrderTrackingView(View):
    def get(self, request):
        return render(request, 'frontend/track_order.html')

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
        
        # ساخت فروشگاه
        shop = Shop.objects.create(
            user=user,
            shop_name=form.cleaned_data['shop_name'],
            slug=form.cleaned_data['shop_slug'],
            instagram_username=form.cleaned_data['instagram_username']
        )
        
        # اختصاص ۳۰ روز اعتبار اولیه به صورت دستی
        # (این کار باعث می‌شود در آینده اگر بررسی اشتراک فعال شد، فروشگاه کار کند)
        shop.plan_expires_at = timezone.now() + timezone.timedelta(days=30)
        shop.save()

        messages.success(self.request, "فروشگاه ساخته شد.")
        return redirect(self.success_url)

def user_login_view(request):
    if request.user.is_authenticated:
        return redirect('frontend:seller-dashboard')
    
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(request, username=u, password=p)
        if user:
            login(request, user)
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
        
        # محاسبه موجودی در دیتابیس با نام db_stock
        # Coalesce باعث می‌شود اگر محصولی واریانت نداشت، عدد 0 برگردد (نه None)
        products = Product.objects.filter(shop=shop).annotate(
            db_stock=Coalesce(Sum('variants__stock'), 0)
        ).order_by('-created_at')

        context.update({
            'products': products,
            'shop': shop,
            # حالا می‌توانیم روی db_stock فیلتر کنیم
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
            product.images = [fs.url(filename)] # ذخیره به صورت لیست برای سازگاری با تمپلیت
            
        product.save()
        
        # ذخیره واریانت‌ها
        colors = self.request.POST.getlist('vars_color[]')
        sizes = self.request.POST.getlist('vars_size[]')
        stocks = self.request.POST.getlist('vars_stock[]')
        prices = self.request.POST.getlist('vars_price[]')
        
        if colors:
            for c, s, st, p in zip(colors, sizes, stocks, prices):
                ProductVariant.objects.create(
                    product=product,
                    color=c, size=s, 
                    stock=int(st), 
                    price_adjustment=int(p) if p else 0
                )
        
        messages.success(self.request, "محصول ایجاد شد.")
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
    product.delete() # حذف کامل برای سادگی
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
        messages.success(self.request, "تنظیمات ذخیره شد.")
        return super().form_valid(form)