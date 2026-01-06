# shops/decorators.py
from django.http import Http404
from django.shortcuts import redirect
from functools import wraps

def shop_required(view_func):
    """
    Decorator for views that require an active shop
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        
        if shop_slug:
            from .models import Shop
            try:
                shop = Shop.objects.get(
                    slug=shop_slug,
                    is_active=True
                )
                request.shop = shop
            except Shop.DoesNotExist:
                raise Http404("Shop not found")
        
        if not hasattr(request, 'shop') or not request.shop:
            raise Http404("Shop not specified")
        
        if not request.shop.is_subscription_active():
            if request.user.is_authenticated and request.user == request.shop.user:
                from django.contrib import messages
                messages.warning(request, "Your subscription has expired. Please renew.")
                return redirect('frontend:seller-dashboard')
            else:
                raise Http404("Shop subscription expired")
        
        return view_func(request, *args, **kwargs)
    return wrapper


def shop_owner_required(view_func):
    """
    Decorator for views that only shop owner can access
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'shop') or not request.shop:
            raise Http404("Shop not found")
        
        if not request.user.is_authenticated or request.user != request.shop.user:
            raise Http404("You don't have permission to access this page")
        
        return view_func(request, *args, **kwargs)
    return wrapper



# shops/decorators.py - بعد از تابع shop_owner_required

def shop_optional(view_func):
    """
    Decorator for views where shop is optional
    If shop exists in URL/session, add it to request, otherwise continue without it
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        shop_slug = kwargs.get('shop_slug')
        
        if shop_slug:
            from .models import Shop
            try:
                shop = Shop.objects.get(
                    slug=shop_slug,
                    is_active=True
                )
                request.shop = shop
            except Shop.DoesNotExist:
                request.shop = None
        else:
            # Check if shop is already set by middleware
            if not hasattr(request, 'shop') or not request.shop:
                # Try to get from session
                shop_id = request.session.get('current_shop_id')
                if shop_id:
                    from .models import Shop
                    try:
                        shop = Shop.objects.get(id=shop_id, is_active=True)
                        request.shop = shop
                    except Shop.DoesNotExist:
                        request.shop = None
                else:
                    request.shop = None
        
        return view_func(request, *args, **kwargs)
    return wrapper