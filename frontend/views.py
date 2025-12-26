import logging
from django.conf import settings
from instastore.utils import ZarinPalService
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
# 1. صفحات عمومی و فروشگاه مشتری
# ==========================================================

class HomeView(TemplateView):
    template_name = 'frontend/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_shops = [s for s in Shop.objects.filter(is_active=True) if s.is_subscription_active()]
        context['featured_shops'] = active_shops[:6]
        return context

class ShopStoreView(TemplateView):
    template_name = 'frontend/shop_store.html'

    def get_context_data(self, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        # نکته: با تغییر url به str، اینجا هم اسلاگ فارسی درست دریافت می‌شود
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)

        if not shop.is_subscription_active():
            raise Http404("این فروشگاه در حال حاضر غیرفعال است (پایان اشتراک).")

        logger.info(f"Shop Visited: {shop.shop_name} (Slug: {shop_slug})")

        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        context['categories'] = Category.objects.filter(
            products__shop=shop, products__is_active=True, products__variants__stock__gt=0
        ).distinct()

        products = Product.objects.filter(shop=shop, is_active=True, variants__stock__gt=0).distinct()

        category_slug = self.request.GET.get('category')
        if category_slug:
            products = products.filter(category__slug=category_slug)

        search_query = self.request.GET.get('q')
        if search_query:
            products = products.filter(name__icontains=search_query)

        context['products'] = products[:24]
        return context

class ProductDetailView(TemplateView):
    template_name = 'frontend/product_detail.html'

    def get_context_data(self, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        product_id = kwargs.get('product_id')
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        
        if not shop.is_subscription_active():
             raise Http404("این فروشگاه در حال حاضر غیرفعال است.")

        product = get_object_or_404(Product, id=product_id, shop=shop, is_active=True)

        context = super().get_context_data(**kwargs)
        context['shop'] = shop
        context['product'] = product
        context['variants'] = product.variants.filter(stock__gt=0)
        context['related_products'] = Product.objects.filter(
            shop=shop, category=product.category, is_active=True
        ).exclude(id=product.id)[:4]

        return context

class CheckoutView(View):
    def get(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        
        if not shop.is_subscription_active():
            messages.error(request, "این فروشگاه در حال حاضر امکان ثبت سفارش ندارد.")
            # اصلاح ریدایرکت با frontend:
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        cart = Cart(request)
        if cart.get_total_items() == 0:
            messages.warning(request, "سبد خرید شما خالی است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)
            
        return render(request, 'frontend/checkout.html', {'shop': shop})

    def post(self, request, shop_slug):
        shop = get_object_or_404(Shop, slug=shop_slug, is_active=True)
        cart = Cart(request)
        
        if not shop.is_subscription_active():
            messages.error(request, "متاسفانه اشتراک این فروشگاه به پایان رسیده است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)
            
        if not shop.can_accept_order():
            messages.error(request, "این فروشگاه به سقف سفارشات ماهانه خود رسیده است.")
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        if cart.get_total_items() == 0:
            return redirect('frontend:shop-store', shop_slug=shop.slug)

        customer_name = request.POST.get('customer_name')
        customer_phone = request.POST.get('customer_phone')
        address = request.POST.get('address')
        note = request.POST.get('note')
        payment_method = request.POST.get('payment_method')

        if not all([customer_name, customer_phone, address, payment_method]):
            messages.error(request, "لطفاً تمام فیلدهای ضروری را پر کنید.")
            return redirect('frontend:checkout', shop_slug=shop.slug)

        try:
            with transaction.atomic():
                order = Order.objects.create(
                    shop=shop,
                    customer=None,
                    status='pending',
                    payment_method=payment_method,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    shipping_address=address,
                    customer_notes=note,
                    total_amount=cart.get_total_price(),
                    subtotal=cart.get_total_price(),
                    shipping_cost=0
                )

                for item in cart:
                    variant_id = item.get('variant_id')
                    if variant_id:
                        variant_obj = ProductVariant.objects.select_for_update().get(id=variant_id)
                        if variant_obj.stock < item['quantity']:
                            raise Exception(f"موجودی ناکافی برای {item['product'].name}")

                        OrderItem.objects.create(
                            order=order,
                            variant=variant_obj,
                            product_name=item['product'].name,
                            size=item['size'],
                            color=item['color'],
                            unit_price=item['price'],
                            quantity=item['quantity'],
                            total_price=item['total_price']
                        )
                        variant_obj.stock -= item['quantity']
                        variant_obj.save()

                cart.clear()
                logger.info(f"New Order Created: #{order.order_id}")

            if payment_method == 'card_to_card':
                messages.success(request, f"سفارش #{order.order_id} ثبت شد. لطفاً مبلغ را کارت به کارت کنید.")
            elif payment_method == 'online':
                messages.info(request, "انتقال به درگاه پرداخت... (دمو)")
            else:
                messages.success(request, f"سفارش #{order.order_id} با موفقیت ثبت شد.")

            return redirect('frontend:shop-store', shop_slug=shop.slug)

        except Exception as e:
            logger.error(f"Checkout Error: {str(e)}", exc_info=True)
            messages.error(request, "خطا در ثبت سفارش. موجودی محصولات را چک کنید.")
            return redirect('frontend:checkout', shop_slug=shop.slug)

# ==========================================================
# 2. پنل فروشنده
# ==========================================================

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
            with transaction.atomic():
                user = form.save(commit=False)
                # user = form.save()
                shop = Shop.objects.create(
                    user=user,
                    shop_name=form.cleaned_data.get('shop_name'),
                    instagram_username=form.cleaned_data.get('instagram_username'),
                    is_active=True
                )
                login(self.request, user)
                messages.success(self.request, f"فروشگاه {shop.shop_name} با موفقیت ساخته شد.")
                return redirect(self.success_url)
        except Exception as e:
            logger.error(f"Registration Error: {str(e)}")
            messages.error(self.request, "خطایی در ثبت فروشگاه رخ داد.")
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
        days_left = shop.remaining_days
        
        if days_left <= 0:
            messages.warning(self.request, "اشتراک شما تمام شده است!")
        elif days_left < 2:
            messages.warning(self.request, f"تنها {days_left} روز از اشتراک باقی مانده است.")

        context.update({
            'shop': shop,
            'total_orders': Order.objects.filter(shop=shop).count(),
            'pending_orders': Order.objects.filter(shop=shop, status='pending').count(),
            'total_products': Product.objects.filter(shop=shop).count(),
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
            
            ProductVariant.objects.create(
                product=product,
                size=form.cleaned_data.get('initial_size', 'Free Size'),
                color=form.cleaned_data.get('initial_color', 'Default'),
                stock=form.cleaned_data.get('initial_stock', 0),
                price_adjustment=0
            )
            messages.success(self.request, 'محصول ایجاد شد')
            return redirect(self.success_url)
        except Exception as e:
            logger.error(f"Product Create Error: {str(e)}")
            messages.error(self.request, "خطا در ایجاد محصول.")
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

    def get_initial(self):
        initial = super().get_initial()
        variant = self.object.variants.first()
        if variant:
            initial['initial_stock'] = variant.stock
            initial['initial_size'] = variant.size
            initial['initial_color'] = variant.color
        return initial

    def form_valid(self, form):
        response = super().form_valid(form)
        variant = self.object.variants.first()
        if variant:
            variant.stock = form.cleaned_data.get('initial_stock', variant.stock)
            variant.size = form.cleaned_data.get('initial_size', variant.size)
            variant.color = form.cleaned_data.get('initial_color', variant.color)
            variant.save()
        return response

@require_http_methods(["DELETE", "POST"])
@login_required
def delete_product(request, pk):
    shop = request.user.shop
    product = get_object_or_404(Product, pk=pk, shop=shop)
    try:
        product.is_active = False
        product.save()
        return JsonResponse({'success': True, 'message': 'محصول آرشیو شد.'})
    except Exception as e:
        logger.error(f"Soft Delete Error: {str(e)}")
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
    # اصلاح ریدایرکت
    success_url = reverse_lazy('frontend:seller-settings')

    def get_object(self):
        return self.request.user.shop

    def form_valid(self, form):
        messages.success(self.request, "تنظیمات فروشگاه ذخیره شد.")
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class SalesReportView(TemplateView):
    template_name = 'frontend/sales_report.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shop = self.request.user.shop
        now = timezone.now()
        month_start = now.replace(day=1)
        month_orders = Order.objects.filter(shop=shop, created_at__gte=month_start)
        month_sales = month_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        context.update({
            'month_sales': month_sales,
            'month_count': month_orders.count(),
            'top_products': month_orders.values('items__product_name').annotate(count=Count('items')).order_by('-count')[:5]
        })
        return context

# ==========================================================
# 3. مدیریت اشتراک و پرداخت
# ==========================================================

@method_decorator(login_required, name='dispatch')
class UpgradePlanView(TemplateView):
    template_name = 'frontend/upgrade_plan.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['plans'] = Plan.objects.filter(is_active=True).exclude(code=Plan.PLAN_FREE)
        context['shop'] = self.request.user.shop
        return context

@login_required
def start_subscription_payment(request, plan_id):
    shop = request.user.shop
    plan = get_object_or_404(Plan, id=plan_id)

    if plan.price == 0:
        shop.renew_subscription(new_plan=plan)
        messages.success(request, f"پلن {plan.name} فعال شد.")
        return redirect('frontend:seller-dashboard')

    request.session['pending_plan_id'] = plan.id
    zarinpal = ZarinPalService()
    # اصلاح آدرس کال‌بک
    callback_url = request.build_absolute_uri(reverse_lazy('frontend:payment-callback'))

    result = zarinpal.send_request(
        amount=plan.price,
        description=f"خرید اشتراک {plan.name}",
        callback_url=callback_url,
        mobile=shop.phone_number,
        email=request.user.email
    )

    if result['status']:
        return redirect(result['url'])
    else:
        messages.error(request, f"خطا در درگاه: {result['message']}")
        return redirect('frontend:upgrade-plan')

@login_required
def payment_callback(request):
    authority = request.GET.get('Authority')
    status = request.GET.get('Status')
    plan_id = request.session.get('pending_plan_id')

    if not plan_id:
        messages.error(request, "نشست خرید منقضی شده.")
        return redirect('frontend:upgrade-plan')

    shop = request.user.shop
    plan = get_object_or_404(Plan, id=plan_id)

    if status != 'OK':
        messages.warning(request, "پرداخت لغو شد.")
        return redirect('frontend:upgrade-plan')

    zarinpal = ZarinPalService()
    verification = zarinpal.verify_payment(authority, plan.price)

    if verification['status']:
        shop.renew_subscription(new_plan=plan)
        del request.session['pending_plan_id']
        messages.success(request, f"اشتراک فعال شد. کد پیگیری: {verification['ref_id']}")
        return redirect('frontend:seller-dashboard')
    else:
        messages.error(request, f"تراکنش ناموفق: {verification['message']}")
        return redirect('frontend:upgrade-plan')

# ==========================================================
# 4. احراز هویت و ابزارها
# ==========================================================

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
        else:
            messages.error(request, "نام کاربری یا رمز عبور اشتباه است.")
    return render(request, 'frontend/login.html')

def logout_view(request):
    logout(request)
    return redirect('frontend:home')

def about_page(request):
    return render(request, 'frontend/about.html')

def contact_page(request):
    return render(request, 'frontend/contact.html')

def get_cart_component(request):
    return render(request, 'partials/cart_badge.html')

# در instastore/frontend/views.py

@require_POST
def add_to_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    
    # 1. چک کردن تداخل فروشگاه
    # اگر سبد خالی نیست، چک کن محصول جدید مال همون فروشگاهِ توی سبد باشه
    if cart.cart: # اگر سبد خالی نیست
        # گرفتن آیدی اولین محصول توی سبد برای نمونه
        first_item_id = next(iter(cart.cart))
        first_item_product = Product.objects.get(id=first_item_id)
        
        # اگر فروشگاه محصول جدید با فروشگاه محصول توی سبد فرق داشت
        if product.shop.id != first_item_product.shop.id:
            cart.clear() # کل سبد قبلی را پاک کن (یا ارور بده)
            # اختیاری: پیامی به کاربر بدهید که "سبد خرید قبلی شما مربوط به فروشگاه دیگری بود و حذف شد."

    qty = int(request.POST.get('quantity', 1))
    size = request.POST.get('size', 'Free Size')
    color = request.POST.get('color', 'Default')
    
    cart.add(product_id=product_id, quantity=qty, size=size, color=color)
    return JsonResponse({'success': True, 'total_items': cart.get_total_items()})

class OrderTrackingView(View):
    def get(self, request):
        return render(request, 'frontend/track_order.html')
    
    def post(self, request):
        order_id = request.POST.get('order_id')
        phone = request.POST.get('phone')
        # اینجا باید لاجیک جستجو را بگذارید. فعلا ساده:
        return render(request, 'frontend/track_order.html', {'message': 'سیستم پیگیری در حال تکمیل است'})