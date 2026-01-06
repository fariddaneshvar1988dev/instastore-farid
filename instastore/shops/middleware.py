# shops/middleware.py
from django.urls import resolve
from .models import Shop
import logging

logger = logging.getLogger('instastore')

class ShopMiddleware:
    """
    Middleware to detect shop from URL slug
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        request.shop = None
        
        try:
            resolved = resolve(request.path_info)
            
            if 'shop_slug' in resolved.kwargs:
                shop_slug = resolved.kwargs['shop_slug']
                
                try:
                    shop = Shop.objects.get(
                        slug=shop_slug,
                        is_active=True
                    )
                    
                    request.shop = shop
                    
                    request.session['current_shop_id'] = shop.id
                    request.session['current_shop_slug'] = shop.slug
                    request.session['current_shop_name'] = shop.shop_name
                    
                    logger.debug(f"ShopMiddleware: Shop '{shop.slug}' detected")
                        
                except Shop.DoesNotExist:
                    logger.warning(f"ShopMiddleware: Shop '{shop_slug}' not found")
                    
        except Exception as e:
            logger.debug(f"ShopMiddleware error: {str(e)}")
        
        response = self.get_response(request)
        return response