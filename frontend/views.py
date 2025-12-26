import logging
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, CreateView, UpdateView, DetailView, View
from django.http import JsonResponse, Http404, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.files.storage import FileSystemStorage
from django.db.models import Sum
from django.contrib.auth import login, logout
from django.db import transaction
from django.utils import timezone

from shops.models import Shop, Plan
from products.models import Product, Category, ProductVariant
from orders.models import Order, OrderItem
from .forms import ProductForm, SellerRegisterForm, ShopSettingsForm

logger = logging.getLogger('instastore')

# ==========================================
# بخش مدیریت سبد خرید (Cart Logic)
# ==========================================

@require_http_methods(["POST"])
def add_to_cart(request, product_id):
    """
    افزودن محصول به سبد خرید با پشتیبانی از واریانت (رنگ و سایز)
    """
    product = get_object_or_404(Product, id=product_id)
    cart = request.session.get('cart', {})
    
    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 1

    variant_id = request.POST.get('variant_id') # دریافت آیدی واریانت از فرم
    
    variant = None
    if variant_id:
        variant = get_object_or_404(ProductVariant, id=variant_id, product=product)

    # 1. ساخت کلید یکتا برای سبد خرید
    if variant:
        # کلید ترکیبی: "IDمحصول-IDواریانت"
        product_key = f"{product.id}-{variant.id}"
    else:
        product_key = str(product.id)
    
    # 2. محاسبه قیمت آیتم
    price = float(product.base_price)
    if variant and variant.price_adjustment:
        price += float(variant.price_adjustment)

    # 3. چک کردن موجودی (اختیاری ولی توصیه شده)
    current_qty_in_cart = 0
    if product_key in cart:
        current_qty_in_cart = cart[product_key]['quantity']
    
    max_stock = variant.stock if variant else product.total_stock
    
    # اگر موجودی کافی بود اضافه کن
    if (current_qty_in_cart + quantity) <= max_stock:
        if product_key in cart:
            cart[product_key]['quantity'] += quantity
        else:
            img_url = product.images[0] if product.images else ''
            
            item_data = {
                'product_id': product.id,
                'name': product.name,
                'price': price,
                'quantity': quantity,
                'image': img_url,
                'shop_slug': product.shop.slug,
            }
            
            # ذخیره اطلاعات رنگ و سایز برای نمایش در سبد
            if variant:
                item_data.update({
                    'variant_id': variant.id,
                    'size': variant.size,
                    'color': variant.color
                })
            
            cart[product_key] = item_data
        
        request.session['cart'] = cart
        request.session.modified = True
    else:
        # اینجا می‌توان پیام خطا لاگ کرد یا هندل کرد (فعلا نادیده می‌گیریم)
        pass

    return render_cart_sidebar(request, cart)

@require_http_methods(["POST"])
def remove_from_cart(request, item_key):
    """
    حذف آیتم از سبد خرید
    ورودی item_key حالا رشته است تا کلیدهای ترکیبی مثل '4-12' را ساپورت کند
    """
    cart = request.session.get('cart', {})
    
    # تبدیل به رشته محض اطمینان
    key_str = str(item_key)
    
    if key_str in cart:
        del cart[key_str]
        request.session['cart'] = cart
        request.session.modified = True
        
    return render_cart_sidebar(request, cart)

def get_cart_sidebar(request):
    """تابع فراخوانی اولیه سایدبار (هنگام لود صفحه)"""
    cart = request.session.get('cart', {})
    return render_cart_sidebar(request, cart)

def render_cart_sidebar(request, cart):
    """تابع کمکی رندر HTML سایدبار"""
    total_items = sum(item['quantity'] for item in cart.values())
    total_price = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # پیدا کردن اسلاگ فروشگاه برای لینک‌های دکمه‌ها
    shop_slug = None
    if cart:
        try:
            first_item = next(iter(cart.values()))
            shop_slug = first_item.get('shop_slug')
        except:
            pass

    context = {
        'cart': cart,
        'cart_total_count': total_items,
        'cart_total_price': total_price,
        'shop_slug': shop_slug,
    }
    return render(request, 'partials/cart_sidebar.html', context)


# ==========================================
# ویوهای فروشگاه (سمت مشتری)
# ==========================================

class ShopStoreView(TemplateView):
    template_name = 'frontend/shop_store.html'

    def get_context_data(self, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        # نکته: با تغییر url به str، اینجا هم اسلاگ فارسی درست دریافت می‌شود
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        
        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        
        # فیلتر محصولات
        products = Product.objects.filter(
            shop=shop, 
            is_active=True,
            variants__stock__gt=0 # فقط محصولاتی که حداقل یک واریانت موجود دارند
        ).distinct()
        
        # فیلتر جستجو و دسته‌بندی
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
        product = get_object_or_404(Product, id=product_id, shop=shop)
        
        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        context['product'] = product
        
        # --- آماده‌سازی داده‌ها برای سیستم انتخاب رنگ و سایز ---
        variants = product.variants.filter(stock__gt=0)
        
        colors = set()
        sizes = set()
        variants_data = []

        for v in variants:
            colors.add(v.color)
            sizes.add(v.size)
            variants_data.append({
                'id': v.id,
                'color': v.color,
                'size': v.size,
                # تغییر مهم: تبدیل Decimal به float برای رفع خطای JSON
                'price_adj': float(v.price_adjustment), 
                'stock': v.stock
            })
            
        context['unique_colors'] = sorted(list(colors))
        context['unique_sizes'] = sorted(list(sizes))
        
        # حالا تبدیل به JSON بدون خطا انجام می‌شود
        context['variants_json'] = json.dumps(variants_data)
        
        context['related_products'] = Product.objects.filter(
            shop=shop, 
            category=product.category, 
            is_active=True
        ).exclude(id=product.id)[:4]
        
        return context
    
class CheckoutView(View):
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = request.session.get('cart', {})
        total_price = sum(item['price'] * item['quantity'] for item in cart.values())
        
        return render(request, 'frontend/checkout.html', {
            'shop': shop, 
            'cart': cart,
            'total_price': total_price
        })

    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = request.session.get('cart', {})
        
        if not cart:
            messages.error(request, "سبد خرید شما خالی است.")
            return redirect('shop-store', shop_slug=shop.slug)

        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')
        address = request.POST.get('address')
        note = request.POST.get('note')

        try:
            # شروع تراکنش اتمیک برای اطمینان از کسر موجودی صحیح
            with transaction.atomic():
                
                # 1. بررسی نهایی موجودی قبل از ثبت
                for key, item in cart.items():
                    variant_id = item.get('variant_id')
                    quantity_needed = item['quantity']
                    
                    if variant_id:
                        # قفل کردن رکورد برای جلوگیری از خرید همزمان (Action 6)
                        variant = ProductVariant.objects.select_for_update().get(id=variant_id)
                        if variant.stock < quantity_needed:
                            messages.error(request, f"متاسفانه موجودی محصول {item['name']} ({item['color']}-{item['size']}) به پایان رسیده یا کمتر از تعداد درخواستی شماست.")
                            return redirect('checkout', shop_slug=shop.slug)
                
                # 2. ایجاد سفارش
                total_amount = sum(item['price'] * item['quantity'] for item in cart.values())
                
                order = Order.objects.create(
                    shop=shop,
                    customer=None, # اگر سیستم مشتری دارید اینجا ست کنید
                    status='pending',
                    payment_method=payment_method,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    shipping_address=address,
                    customer_notes=note,
                    total_amount=total_amount,
                    subtotal=total_amount,
                    shipping_cost=0
                )

                # 3. ثبت آیتم‌ها و کسر موجودی
                for key, item in cart.items():
                    variant = None
                    if item.get('variant_id'):
                        variant = ProductVariant.objects.get(id=item['variant_id'])
                        
                        # کسر موجودی نهایی
                        variant.stock -= item['quantity']
                        variant.save()

                    OrderItem.objects.create(
                        order=order,
                        variant=variant,
                        product_name=item['name'],
                        size=item.get('size', 'استاندارد'),
                        color=item.get('color', 'پیش‌فرض'),
                        unit_price=item['price'],
                        quantity=item['quantity'],
                        total_price=item['price'] * item['quantity']
                    )

                logger.info(f"New Order Placed: #{order.order_id}")
                
                # 4. خالی کردن سبد خرید
                del request.session['cart']
                request.session.modified = True

            messages.success(request, f"سفارش شما با شماره {order.order_id} با موفقیت ثبت شد.")
            return redirect('shop-store', shop_slug=shop.slug)

        except Exception as e:
            logger.error(f"Checkout Error: {str(e)}", exc_info=True)
            messages.error(request, "خطایی در ثبت سفارش رخ داد. لطفا دوباره تلاش کنید.")
            return redirect('checkout', shop_slug=shop.slug)


# ==========================================
# سایر ویوها (صفحه اصلی، پنل فروشنده و...)
# ==========================================

class HomeView(TemplateView):
    template_name = 'frontend/home.html'

def about_page(request):
    return render(request, 'frontend/about.html')

def contact_page(request):
    return render(request, 'frontend/contact.html')

# --- پنل فروشنده ---

class SellerRegisterView(CreateView):
    template_name = 'frontend/register.html'
    form_class = SellerRegisterForm
    # اصلاح ریدایرکت
    success_url = reverse_lazy('frontend:seller-dashboard')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, 'shop'):
            return redirect('frontend:seller-dashboard')
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
            
            login(self.request, user)
            messages.success(self.request, f"فروشگاه «{shop_name}» ساخته شد.")
            return redirect(self.success_url)
            
        except Exception as e:
            logger.error(f"Registration Error: {str(e)}")
            messages.error(self.request, "خطایی رخ داد.")
            return self.form_invalid(form)

@method_decorator(login_required, name='dispatch')
class SellerDashboardView(TemplateView):
    template_name = 'frontend/seller_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'shop'):
            messages.info(request, "برای دسترسی به داشبورد، ابتدا باید فروشگاه خود را بسازید.")
            return redirect('frontend:register-page')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        context.update({
            'shop': shop,
            'total_orders': Order.objects.filter(shop=shop).count(),
            'pending_orders': Order.objects.filter(shop=shop, status='pending').count(),
            'total_products': Product.objects.filter(shop=shop).count(),
            'low_stock_products': Product.objects.filter(shop=shop).annotate(total_stock=Sum('variants__stock')).filter(total_stock__lt=5).count(),
            'recent_orders': Order.objects.filter(shop=shop).order_by('-created_at')[:5],
        })
        return context

@method_decorator(login_required, name='dispatch')
class SellerProductsView(TemplateView):
    template_name = 'frontend/seller_products.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        context['products'] = Product.objects.filter(shop=shop, is_active=True)
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

@method_decorator(login_required, name='dispatch')
class SellerProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend/seller_product_form.html'
    # اصلاح ریدایرکت
    success_url = reverse_lazy('frontend:seller-products')

    def dispatch(self, request, *args, **kwargs):
        shop = request.user.shop
        if not shop.can_add_product():
            messages.error(request, "شما به سقف تعداد محصولات پلن خود رسیده‌اید.")
            return redirect('frontend:upgrade-plan')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.user.shop
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                product = form.save(commit=False)
                product.shop = self.request.user.shop
                
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
                
                colors = self.request.POST.getlist('vars_color[]')
                sizes = self.request.POST.getlist('vars_size[]')
                stocks = self.request.POST.getlist('vars_stock[]')
                prices = self.request.POST.getlist('vars_price[]')
                
                if colors and len(colors) > 0:
                    for c, s, st, p in zip(colors, sizes, stocks, prices):
                        p_adj = int(p) if p and p.strip() else 0
                        st_val = int(st) if st and st.strip() else 0
                        
                        ProductVariant.objects.create(
                            product=product,
                            color=c,
                            size=s,
                            stock=st_val,
                            price_adjustment=p_adj
                        )
                else:
                    ProductVariant.objects.create(
                        product=product,
                        color="پیش‌فرض",
                        size="استاندارد",
                        stock=0,
                        price_adjustment=0
                    )

                messages.success(self.request, 'محصول با موفقیت ایجاد شد')
                return redirect(self.success_url)
                
        except Exception as e:
            logger.error(f"Product Create Error: {str(e)}")
            messages.error(self.request, "خطایی در ذخیره محصول رخ داد.")
            return self.form_invalid(form)

@method_decorator(login_required, name='dispatch')
class SellerProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'frontend/seller_product_form.html'
    # اصلاح ریدایرکت
    success_url = reverse_lazy('frontend:seller-products')

    def get_queryset(self):
        return Product.objects.filter(shop=self.request.user.shop)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['shop'] = self.request.user.shop
        return kwargs

@require_http_methods(["DELETE", "POST"])
@login_required
def delete_product(request, pk):
    shop = request.user.shop
    product = get_object_or_404(Product, pk=pk, shop=shop)
    try:
        product.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False}, status=500)

@method_decorator(login_required, name='dispatch')
class SellerOrdersView(TemplateView):
    template_name = 'frontend/seller_orders.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        status_filter = self.request.GET.get('status', 'all')
        orders = Order.objects.filter(shop=shop)
        if status_filter != 'all':
            orders = orders.filter(status=status_filter)
        context.update({'shop': shop, 'orders': orders.order_by('-created_at'), 'status_filter': status_filter})
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
    success_url = reverse_lazy('seller-settings')
    def get_object(self):
        return self.request.user.shop
    def form_valid(self, form):
        messages.success(self.request, "تنظیمات ذخیره شد.")
        return super().form_valid(form)

def logout_view(request):
    logout(request)
    return redirect('frontend:home')

def about_page(request):
    return render(request, 'frontend/about.html')

def contact_page(request):
    return render(request, 'frontend/contact.html')

def get_cart_component(request):
    return render(request, 'partials/cart_badge.html')

def cart_detail_view(request):
    cart = request.session.get('cart', [])
    return render(request, 'frontend/cart_detail.html', {'cart': cart})

@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    template_name = 'frontend/profile.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user
        if hasattr(user, 'shop'):
            context['shop'] = user.shop
            context['is_seller'] = True
        else:
            context['is_seller'] = False
        return context

# API های اضافی (Placeholder)
@require_http_methods(["GET"])
def load_more_products(request, shop_slug):
    return JsonResponse({'html': ''}) 
@require_http_methods(["GET"])
def search_products(request, shop_slug):
    return JsonResponse({'html': ''})