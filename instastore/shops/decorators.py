"""
Decoratorهای مدیریت دسترسی فروشگاه‌ها
برای پلتفرم مولتی‌تیننسی با سیستم اشتراک
"""

from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from functools import wraps
from datetime import timedelta
import logging

logger = logging.getLogger('instastore')

# ------------------------------------------------------------
# 1. Decoratorهای اصلی دسترسی
# ------------------------------------------------------------

def shop_access(view_func):
    """
    پایه‌ای‌ترین decorator - فقط وجود فروشگاه را بررسی می‌کند
    مناسب برای: مشاهده عمومی فروشگاه، محصولات
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        
        if not shop_slug:
            # اگر shop_slug در URL نیست، بررسی کن شاید در session باشد
            if hasattr(request, 'session') and 'current_shop_slug' in request.session:
                shop_slug = request.session['current_shop_slug']
            else:
                raise Http404("فروشگاه مشخص نشده است")
        
        try:
            from .models import Shop
            shop = Shop.objects.select_related('current_plan', 'user').get(
                slug=shop_slug,
                is_active=True  # فقط فروشگاه‌های فعال
            )
            request.shop = shop
            
            # ذخیره در session برای دسترسی‌های بعدی
            if hasattr(request, 'session'):
                request.session['current_shop_id'] = shop.id
                request.session['current_shop_slug'] = shop.slug
                request.session['current_shop_name'] = shop.shop_name
            
        except Shop.DoesNotExist:
            logger.warning(f"Shop not found: {shop_slug}")
            raise Http404("فروشگاه یافت نشد")
        except Exception as e:
            logger.error(f"Error accessing shop {shop_slug}: {str(e)}")
            raise Http404("خطا در بارگذاری فروشگاه")
        
        return view_func(request, *args, **kwargs)
    return wrapper


def shop_subscription_required(view_func):
    """
    برای عملیات‌هایی که نیاز به اشتراک فعال دارند
    مناسب برای: ثبت سفارش جدید، افزودن محصول
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # اول shop را پیدا کن
        shop_access_wrapper = shop_access(view_func)
        response = shop_access_wrapper(request, *args, **kwargs)
        
        # اگر view اجرا شده و بازگشته، بررسی کن
        if hasattr(request, 'shop') and request.shop:
            shop = request.shop
            
            # فقط برای صاحب فروشگاه بررسی کن
            is_owner = (
                request.user.is_authenticated and 
                hasattr(request.user, 'shop') and 
                request.user.shop == shop
            )
            
            if is_owner and not shop.is_subscription_active:
                # اگر مالک است و اشتراک منقضی شده
                messages.error(
                    request,
                    f"برای انجام این عملیات نیاز به اشتراک فعال دارید. "
                    f"({shop.remaining_days} روز باقی مانده)"
                )
                
                # اگر درخواست AJAX است
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'error': True,
                        'message': 'اشتراک شما منقضی شده است',
                        'redirect': '/seller/plans/'
                    }, status=403)
                
                # ریدایرکت به صفحه پلن‌ها
                return redirect('frontend:seller-plans')
        
        return response
    return wrapper


def shop_owner_required(view_func):
    """
    فقط صاحب فروشگاه می‌تواند دسترسی داشته باشد
    مناسب برای: پنل مدیریت فروشگاه، تنظیمات
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # اول shop را پیدا کن
        shop_access_wrapper = shop_access(view_func)
        
        try:
            response = shop_access_wrapper(request, *args, **kwargs)
        except Http404:
            raise Http404("فروشگاه یافت نشد")
        
        # بررسی مالکیت
        if hasattr(request, 'shop') and request.shop:
            shop = request.shop
            
            if not request.user.is_authenticated:
                return redirect(f'/login/?next={request.path}')
            
            # بررسی مالکیت
            is_owner = (
                hasattr(request.user, 'shop') and 
                request.user.shop == shop
            )
            
            if not is_owner:
                logger.warning(
                    f"Unauthorized access attempt to shop {shop.slug} "
                    f"by user {request.user.username}"
                )
                raise Http404("شما اجازه دسترسی به این صفحه را ندارید")
        
        return response
    return wrapper


def shop_owner_or_staff(view_func):
    """
    صاحب فروشگاه یا ادمین پلتفرم
    مناسب برای: گزارش‌ها، آمار پیشرفته
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # اول shop را پیدا کن
        shop_access_wrapper = shop_access(view_func)
        
        try:
            response = shop_access_wrapper(request, *args, **kwargs)
        except Http404:
            raise Http404("فروشگاه یافت نشد")
        
        # بررسی دسترسی
        if hasattr(request, 'shop') and request.shop:
            shop = request.shop
            
            if not request.user.is_authenticated:
                return redirect(f'/login/?next={request.path}')
            
            # بررسی مالکیت یا staff بودن
            is_owner = (
                hasattr(request.user, 'shop') and 
                request.user.shop == shop
            )
            
            is_staff = request.user.is_staff or request.user.is_superuser
            
            if not (is_owner or is_staff):
                logger.warning(
                    f"Unauthorized access attempt to shop {shop.slug} "
                    f"by non-staff user {request.user.username}"
                )
                raise Http404("شما اجازه دسترسی به این صفحه را ندارید")
        
        return response
    return wrapper


# ------------------------------------------------------------
# 2. Decoratorهای ویژه برای سیستم اشتراک
# ------------------------------------------------------------

def require_active_subscription(view_func):
    """
    حتماً باید اشتراک فعال باشد
    مناسب برای: API‌های حیاتی
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'shop') or not request.shop:
            raise Http404("فروشگاه مشخص نیست")
        
        shop = request.shop
        
        if not shop.is_subscription_active:
            logger.warning(
                f"Expired subscription attempt: shop {shop.slug}, "
                f"user {request.user.username if request.user.is_authenticated else 'anonymous'}"
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': True,
                    'code': 'SUBSCRIPTION_EXPIRED',
                    'message': 'اشتراک فروشگاه منقضی شده است',
                    'remaining_days': shop.remaining_days,
                    'expires_at': shop.plan_expires_at.isoformat() if shop.plan_expires_at else None
                }, status=402)  # 402 Payment Required
            
            # نمایش صفحه ویژه انقضای اشتراک
            from django.shortcuts import render
            return render(request, 'frontend/subscription_expired.html', {
                'shop': shop,
                'remaining_days': shop.remaining_days
            })
        
        return view_func(request, *args, **kwargs)
    return wrapper


def check_plan_limits(view_func):
    """
    بررسی محدودیت‌های پلن قبل از انجام عملیات
    مناسب برای: اضافه کردن محصول، ثبت سفارش
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'shop') or not request.shop:
            raise Http404("فروشگاه مشخص نیست")
        
        shop = request.shop
        
        # بررسی اشتراک
        if not shop.is_subscription_active:
            messages.error(request, "اشتراک شما منقضی شده است. لطفاً تمدید کنید.")
            return redirect('frontend:seller-plans')
        
        # بررسی محدودیت محصولات
        if 'add_product' in request.path or 'create_product' in request.path:
            if not shop.can_add_product():
                messages.error(
                    request,
                    f"به حد مجاز محصولات ({shop.current_plan.max_products}) رسیده‌اید. "
                    f"لطفاً پلن خود را ارتقا دهید."
                )
                return redirect('frontend:seller-plans')
        
        # بررسی محدودیت سفارشات
        if 'checkout' in request.path or 'create_order' in request.path:
            if not shop.can_accept_order():
                messages.error(
                    request,
                    f"به حد مجاز سفارشات ماهانه ({shop.current_plan.max_orders_per_month}) رسیده‌اید. "
                    f"لطفاً پلن خود را ارتقا دهید."
                )
                return redirect('frontend:seller-plans')
        
        return view_func(request, *args, **kwargs)
    return wrapper


# ------------------------------------------------------------
# 3. Decoratorهای کمکی و ابزاری
# ------------------------------------------------------------

def shop_optional(view_func):
    """
    فروشگاه اختیاری است - اگر وجود داشت اضافه کن
    مناسب برای: صفحات عمومی که ممکن است کاربر در یک فروشگاه باشد
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        
        if shop_slug:
            try:
                from .models import Shop
                shop = Shop.objects.select_related('current_plan').get(
                    slug=shop_slug,
                    is_active=True
                )
                request.shop = shop
                
                # ذخیره در session
                if hasattr(request, 'session'):
                    request.session['current_shop_id'] = shop.id
                    request.session['current_shop_slug'] = shop.slug
                
            except Shop.DoesNotExist:
                request.shop = None
        else:
            # بررسی session
            if hasattr(request, 'session') and 'current_shop_slug' in request.session:
                try:
                    from .models import Shop
                    shop = Shop.objects.get(
                        slug=request.session['current_shop_slug'],
                        is_active=True
                    )
                    request.shop = shop
                except Shop.DoesNotExist:
                    request.shop = None
            else:
                request.shop = None
        
        return view_func(request, *args, **kwargs)
    return wrapper


def track_shop_activity(view_func):
    """
    ردیابی فعالیت‌های فروشگاه برای آنالیتیکس
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # اگر فروشگاه وجود دارد، فعالیت را ثبت کن
        if hasattr(request, 'shop') and request.shop:
            from .models import ShopActivity
            try:
                ShopActivity.objects.create(
                    shop=request.shop,
                    user=request.user if request.user.is_authenticated else None,
                    action=request.path,
                    method=request.method,
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:200]
                )
            except Exception as e:
                logger.error(f"Failed to log shop activity: {str(e)}")
        
        return response
    return wrapper


# ------------------------------------------------------------
# 4. ترکیب decoratorها برای استفاده‌های رایج
# ------------------------------------------------------------

def public_shop_view(view_func):
    """
    ترکیب decorator برای مشاهده عمومی فروشگاه
    """
    @wraps(view_func)
    @shop_access
    @track_shop_activity
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


def seller_shop_view(view_func):
    """
    ترکیب decorator برای پنل فروشنده
    """
    @wraps(view_func)
    @shop_owner_required
    @shop_access
    @track_shop_activity
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


def seller_shop_action(view_func):
    """
    ترکیب decorator برای عملیات فروشنده که نیاز به اشتراک فعال دارد
    """
    @wraps(view_func)
    @shop_owner_required
    @shop_access
    @check_plan_limits
    @track_shop_activity
    def wrapper(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return wrapper


# ------------------------------------------------------------
# 5. Middleware-like decorator برای بررسی انقضای اشتراک
# ------------------------------------------------------------

def subscription_check_middleware(get_response):
    """
    Middleware-style decorator برای بررسی مداوم وضعیت اشتراک
    """
    def middleware(request):
        response = get_response(request)
        
        # اگر کاربر در پنل فروشنده است و اشتراکش منقضی شده
        if (request.user.is_authenticated and 
            hasattr(request.user, 'shop') and 
            'seller' in request.path):
            
            shop = request.user.shop
            
            # اگر اشتراک منقضی شده
            if not shop.is_subscription_active:
                # فقط یک بار در session علامت بزن که هشدار دادی
                warning_shown = request.session.get('subscription_warning_shown', False)
                
                if not warning_shown and shop.remaining_days == 0:
                    messages.error(
                        request,
                        "⏰ اشتراک شما منقضی شده است! لطفاً برای ادامه فعالیت تمدید کنید."
                    )
                    request.session['subscription_warning_shown'] = True
                
                elif not warning_shown and shop.remaining_days <= 3:
                    messages.warning(
                        request,
                        f"⚠️ فقط {shop.remaining_days} روز تا انقضای اشتراک شما باقی مانده است."
                    )
                    request.session['subscription_warning_shown'] = True
            
            # اگر هشدار نشان داده شده و کاربر اشتراکش را تمدید کرده
            elif request.session.get('subscription_warning_shown', False):
                request.session['subscription_warning_shown'] = False
        
        return response
    
    return middleware


# ------------------------------------------------------------
# 6. Utility functions برای استفاده در viewها
# ------------------------------------------------------------

def get_current_shop(request):
    """
    دریافت فروشگاه جاری از request
    """
    if hasattr(request, 'shop') and request.shop:
        return request.shop
    
    # بررسی session
    if hasattr(request, 'session') and 'current_shop_slug' in request.session:
        try:
            from .models import Shop
            return Shop.objects.get(
                slug=request.session['current_shop_slug'],
                is_active=True
            )
        except Shop.DoesNotExist:
            pass
    
    return None


def require_shop_context(view_func):
    """
    تضمین می‌کند که shop در context وجود دارد
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        
        # اگر response یک TemplateResponse است
        if hasattr(response, 'context_data'):
            if 'shop' not in response.context_data and hasattr(request, 'shop'):
                response.context_data['shop'] = request.shop
        
        return response
    return wrapper


# ------------------------------------------------------------
# 7. مدیریت خطاها و exceptions
# ------------------------------------------------------------

def handle_shop_exceptions(view_func):
    """
    مدیریت خطاهای مرتبط با فروشگاه
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        try:
            return view_func(request, *args, **kwargs)
        
        except Http404 as e:
            logger.warning(f"Shop not found: {request.path}")
            raise
        
        except Exception as e:
            logger.error(f"Shop view error: {str(e)}")
            
            # اگر فروشگاه وجود دارد، لاگ کن
            if hasattr(request, 'shop') and request.shop:
                from .models import ShopErrorLog
                ShopErrorLog.objects.create(
                    shop=request.shop,
                    user=request.user if request.user.is_authenticated else None,
                    path=request.path,
                    error_message=str(e)[:500],
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
            
            # نمایش صفحه خطا
            from django.shortcuts import render
            return render(request, 'frontend/error.html', {
                'error': 'خطا در بارگذاری فروشگاه',
                'message': 'لطفاً بعداً تلاش کنید'
            }, status=500)
    
    return wrapper




def shop_required(view_func):
    """
    Decorator برای views که نیاز به یک فروشگاه فعال دارند.
    فروشگاه از طریق request.shop (توسط middleware) باید شناسایی شده باشد.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not hasattr(request, 'shop') or request.shop is None:
            # در اینجا میتوانید به صفحه انتخاب فروشگاه یا خطا ریدایرکت کنید
            return HttpResponseForbidden("دسترسی به فروشگاه لازم است")
        return view_func(request, *args, **kwargs)
    return _wrapped_view