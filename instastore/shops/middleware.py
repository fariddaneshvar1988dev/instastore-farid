from django.http import Http404
from .models import Shop

class ShopMiddleware:
    """
    Middleware برای تشخیص فروشگاه از روی slug در URL
    به تمام درخواست‌های API اضافه می‌شود
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # فقط برای API‌ها اعمال شود
        if request.path.startswith('/api/shop/'):
            try:
                # استخراج slug از URL
                # مثال: /api/shop/{slug}/products/
                path_parts = request.path.split('/')
                if len(path_parts) >= 4:
                    shop_slug = path_parts[3]
                    
                    # پیدا کردن فروشگاه
                    shop = Shop.objects.get(
                        slug=shop_slug,
                        is_active=True
                    )
                    
                    # اضافه کردن فروشگاه به درخواست
                    request.shop = shop
                    
            except (IndexError, Shop.DoesNotExist):
                # اگر فروشگاه پیدا نشد، 404 برگردان
                raise Http404("فروشگاه یافت نشد")
        
        response = self.get_response(request)
        return response