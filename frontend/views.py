import logging
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView
from django.views import View
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
from django.contrib.auth import login, logout
from django.utils.text import slugify
from django.db import transaction

from shops.models import Shop
from products.models import Product, Category, ProductVariant
from orders.models import Order, OrderItem
from .forms import ProductForm, SellerRegisterForm

# ایجاد لاگر اختصاصی (مطابق با settings.py)
logger = logging.getLogger('instastore')

# ========== صفحات عمومی و مشتری ==========

class HomeView(TemplateView):
    template_name = 'frontend/home.html'
    
    def get_context_data(self, **kwargs):
        # لاگ بازدید صفحه اصلی (اختیاری)
        # logger.info("Homepage visited")
        context = super().get_context_data(**kwargs)
        context['featured_shops'] = Shop.objects.filter(is_active=True)[:6]
        return context

class ShopStoreView(TemplateView):
    template_name = 'frontend/shop_store.html'
    
    def get_context_data(self, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        
        # لاگ بازدید از فروشگاه
        logger.info(f"Shop Visited: {shop.shop_name} (Slug: {shop_slug})")
        
        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        
        context['categories'] = Category.objects.filter(
            products__shop=shop, 
            products__is_active=True,
            products__variants__stock__gt=0
        ).distinct()
        
        products = Product.objects.filter(
            shop=shop, 
            is_active=True,
            variants__stock__gt=0
        ).distinct()
        
        # فیلتر دسته‌بندی
        category_slug = self.request.GET.get('category')
        if category_slug:
             products = products.filter(category__slug=category_slug)

        # جستجو + لاگ جستجو
        search_query = self.request.GET.get('q')
        if search_query:
            products = products.filter(name__icontains=search_query)
            logger.info(f"Search in shop '{shop.shop_name}': {search_query}")
        
        context['products'] = products[:24]
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
        context['related_products'] = Product.objects.filter(
            shop=shop, 
            category=product.category, 
            is_active=True,
            variants__stock__gt=0
        ).exclude(id=product.id).distinct()[:4]
        
        return context

class CheckoutView(View):
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        
        # برای تست: انتخاب اولین محصول موجود
        sample_product = Product.objects.filter(shop=shop, is_active=True, variants__stock__gt=0).first()
        
        return render(request, 'frontend/checkout.html', {
            'shop': shop, 
            'sample_product': sample_product
        })

    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        
        # 1. دریافت داده‌های فرم
        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')
        address = request.POST.get('address')
        note = request.POST.get('note')

        # 2. پیدا کردن محصول (فعلاً ساده‌سازی شده)
        product = Product.objects.filter(shop=shop, is_active=True, variants__stock__gt=0).first()
        if not product:
            logger.warning(f"Checkout Failed: No product available in shop {shop.shop_name}")
            messages.error(request, "محصولی برای خرید موجود نیست.")
            return redirect('shop-store', shop_slug=shop.slug)

        variant = product.variants.filter(stock__gt=0).first()
        quantity = 1
        price = variant.final_price

        try:
            with transaction.atomic():
                # 3. ساخت سفارش
                order = Order.objects.create(
                    shop=shop,
                    customer=None, # کاربر مهمان
                    status='pending',
                    payment_method='cash_on_delivery',
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    shipping_address=address,
                    customer_notes=note,
                    total_amount=price * quantity,
                    subtotal=price * quantity,
                    shipping_cost=0
                )

                # 4. ساخت آیتم سفارش
                OrderItem.objects.create(
                    order=order,
                    variant=variant,
                    product_name=product.name,
                    size=variant.size,
                    color=variant.color,
                    unit_price=price,
                    quantity=quantity,
                    total_price=price * quantity
                )

                # 5. کسر موجودی
                variant.stock -= quantity
                variant.save()

                # --- لاگ موفقیت آمیز سفارش ---
                logger.info(f"New Order Placed: #{order.order_id} | Shop: {shop.shop_name} | Amount: {order.total_amount}")

            messages.success(request, f"سفارش شما با شماره {order.order_id} با موفقیت ثبت شد.")
            return redirect('shop-store', shop_slug=shop.slug)

        except Exception as e:
            # --- لاگ خطا ---
            logger.error(f"Checkout Exception in shop {shop.shop_name}: {str(e)}", exc_info=True)
            messages.error(request, "متاسفانه خطایی در ثبت سفارش رخ داد.")
            return redirect('checkout', shop_slug=shop.slug)

def about_page(request):
    return render(request, 'frontend/about.html')

def contact_page(request):
    return render(request, 'frontend/contact.html')

# ========== API ها ==========

@require_http_methods(["GET"])
def load_more_products(request, shop_slug):
    return JsonResponse({'html': ''}) 

@require_http_methods(["GET"])
def search_products(request, shop_slug):
    return JsonResponse({'html': ''})

@require_http_methods(["POST"])
def add_to_cart(request, product_id):
    return JsonResponse({'success': True})

# ========== پنل فروشنده (Seller Dashboard) ==========

class SellerRegisterView(CreateView):
    template_name = 'frontend/register.html'
    form_class = SellerRegisterForm
    success_url = reverse_lazy('seller-dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if hasattr(request.user, 'shop'):
                return redirect('seller-dashboard')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            user = form.save()
            
            shop_name = form.cleaned_data.get('shop_name')
            shop_slug = form.cleaned_data.get('shop_slug')
            insta_id = form.cleaned_data.get('instagram_username')
            
            final_slug = shop_slug
            if Shop.objects.filter(slug=final_slug).exists():
                final_slug = f"{shop_slug}-{user.id}"

            Shop.objects.create(
                user=user,  
                shop_name=shop_name,
                slug=final_slug,
                instagram_username=insta_id,
                is_active=True
            )
            
            # --- لاگ ثبت نام ---
            logger.info(f"New Shop Registered: {shop_name} (User: {user.username}, Slug: {final_slug})")
            
            login(self.request, user)
            messages.success(self.request, f"فروشگاه «{shop_name}» با موفقیت ساخته شد.")
            return redirect(self.success_url)
            
        except Exception as e:
            logger.error(f"Registration Error: {str(e)}", exc_info=True)
            messages.error(self.request, "خطایی در ثبت فروشگاه رخ داد.")
            return self.form_invalid(form)

@method_decorator(login_required, name='dispatch')
class SellerDashboardView(TemplateView):
    template_name = 'frontend/seller_dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'shop'):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        
        # آمارها
        total_orders = Order.objects.filter(shop=shop).count()
        pending_orders = Order.objects.filter(shop=shop, status='pending').count()
        total_products = Product.objects.filter(shop=shop).count()
        
        # محاسبه محصولات کم‌موجودی
        low_stock_products = Product.objects.filter(shop=shop).annotate(
            total_stock=Sum('variants__stock')
        ).filter(total_stock__lt=5).count()
        
        context.update({
            'shop': shop,
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'total_products': total_products,
            'low_stock_products': low_stock_products,
            'recent_orders': Order.objects.filter(shop=shop).order_by('-created_at')[:5],
        })
        return context

@method_decorator(login_required, name='dispatch')
class SellerProductsView(TemplateView):
    template_name = 'frontend/seller_products.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'shop'):
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        products = Product.objects.filter(shop=shop)
        
        context['available_count'] = products.filter(is_active=True, variants__stock__gt=0).distinct().count()
        context['out_of_stock_count'] = products.exclude(variants__stock__gt=0).count()
        context['products'] = products
        context['shop'] = shop
        return context

@method_decorator(login_required, name='dispatch')
class SellerOrdersView(TemplateView):
    template_name = 'frontend/seller_orders.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'shop'):
            return redirect('home')
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

# --- مدیریت محصولات ---

@method_decorator(login_required, name='dispatch')
class SellerProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend/seller_product_form.html'
    success_url = reverse_lazy('seller-products')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.user.shop
        return kwargs

    def form_valid(self, form):
        try:
            product = form.save(commit=False)
            product.shop = self.request.user.shop
            
            # ذخیره تصاویر (ساده شده)
            fs = FileSystemStorage()
            images = []
            for i in range(1, 4):
                img_field = self.request.FILES.get(f'image{i}')
                if img_field:
                    filename = fs.save(f"products/{img_field.name}", img_field)
                    images.append(fs.url(filename))
            
            if images:
                product.images = images
                
            product.save()
            
            # ایجاد اولین واریانت
            ProductVariant.objects.create(
                product=product,
                size=form.cleaned_data.get('initial_size', 'Free Size'),
                color=form.cleaned_data.get('initial_color', 'Default'),
                stock=form.cleaned_data.get('initial_stock', 0),
                price_adjustment=0
            )

            # --- لاگ ایجاد محصول ---
            logger.info(f"Product Created: {product.name} (Shop: {product.shop.shop_name})")
            
            messages.success(self.request, 'محصول با موفقیت ایجاد شد')
            return redirect(self.success_url)
            
        except Exception as e:
            logger.error(f"Product Create Error: {str(e)}", exc_info=True)
            messages.error(self.request, "خطایی در ذخیره محصول رخ داد.")
            return self.form_invalid(form)

@method_decorator(login_required, name='dispatch')
class SellerProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend/seller_product_form.html'
    success_url = reverse_lazy('seller-products')

    def get_queryset(self):
        return Product.objects.filter(shop=self.request.user.shop)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.user.shop
        return kwargs
    
    def form_valid(self, form):
        # --- لاگ آپدیت محصول ---
        logger.info(f"Product Updated: {form.instance.name} (ID: {form.instance.id})")
        return super().form_valid(form)

@require_http_methods(["DELETE", "POST"])
@login_required
def delete_product(request, pk):
    shop = request.user.shop
    product = get_object_or_404(Product, pk=pk, shop=shop)
    
    try:
        name = product.name
        product.delete()
        # --- لاگ حذف محصول ---
        logger.info(f"Product Deleted: {name} (ID: {pk}, Shop: {shop.shop_name})")
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f"Product Delete Error: {str(e)}", exc_info=True)
        return JsonResponse({'success': False}, status=500)

@method_decorator(login_required, name='dispatch')
class SellerOrderDetailView(DetailView):
    model = Order
    template_name = 'frontend/seller_order_detail.html'
    context_object_name = 'order'

    def get_queryset(self):
        return Order.objects.filter(shop=self.request.user.shop)

def logout_view(request):
    if request.user.is_authenticated:
        logger.info(f"User Logout: {request.user.username}")
    logout(request)
    return redirect('home')

def get_cart_component(request):
    return render(request, 'partials/cart_badge.html')