from decimal import Decimal
from django.conf import settings
from products.models import Product, ProductVariant
from shops.models import Shop
import logging

logger = logging.getLogger('instastore')

class Cart:
    """
    کلاس سبد خرید - کاملاً ایزوله برای هر فروشگاه
    """
    def __init__(self, request, shop=None):
        self.session = request.session
        self.request = request
        
        # تشخیص shop
        if shop:
            self.shop = shop
        elif hasattr(request, 'shop') and request.shop:
            self.shop = request.shop
        else:
            # سعی کن از session بگیر
            shop_id = self.session.get('current_shop_id')
            if shop_id:
                try:
                    self.shop = Shop.objects.get(id=shop_id, is_active=True)
                except Shop.DoesNotExist:
                    raise ValueError("فروشگاه معتبر نیست یا غیرفعال شده است")
            else:
                raise ValueError("سبد خرید نیاز به شناسه فروشگاه دارد")
        
        # کلید مخصوص این فروشگاه در session
        self.cart_key = f'cart_shop_{self.shop.id}'
        
        # بارگذاری سبد خرید از session
        cart = self.session.get(self.cart_key)
        if not cart:
            cart = self.session[self.cart_key] = {}
        self.cart = cart
        
        logger.debug(f"Cart initialized for shop: {self.shop.slug} (key: {self.cart_key})")
    
    def add(self, product, variant, quantity=1, override_quantity=False):
        """
        افزودن محصول به سبد خرید با بررسی مالکیت
        """
        # 🔥 بررسی مهم: محصول متعلق به همین فروشگاه باشد
        if product.shop_id != self.shop.id:
            logger.error(f"Attempt to add product from different shop. Product shop: {product.shop_id}, Cart shop: {self.shop.id}")
            raise ValueError("محصول متعلق به این فروشگاه نیست")
        
        # بررسی موجودیت variant
        if variant.product_id != product.id:
            raise ValueError("این تنوع متعلق به این محصول نیست")
        
        item_key = str(variant.id)
        
        if item_key not in self.cart:
            self.cart[item_key] = {
                'quantity': 0,
                'price': str(product.base_price + variant.price_adjustment),
                'product_id': product.id,
                'variant_id': variant.id,
                'added_at': self.request.session.get('cart_timestamp', '')  # برای لاگ
            }
        
        if override_quantity:
            self.cart[item_key]['quantity'] = quantity
        else:
            self.cart[item_key]['quantity'] += quantity
        
        self.save()
        
        logger.debug(f"Product added to cart: {product.name}, variant: {variant.id}, quantity: {self.cart[item_key]['quantity']}")
    
    def save(self):
        """ذخیره تغییرات در session"""
        self.session.modified = True
    
    def remove(self, variant_id):
        """حذف آیتم از سبد خرید"""
        item_key = str(variant_id)
        if item_key in self.cart:
            # بررسی مالکیت قبل از حذف
            try:
                variant = ProductVariant.objects.get(id=variant_id)
                if variant.product.shop_id != self.shop.id:
                    logger.warning(f"Attempt to remove item from different shop. Item shop: {variant.product.shop_id}, Cart shop: {self.shop.id}")
                    return False
            except ProductVariant.DoesNotExist:
                pass
            
            del self.cart[item_key]
            self.save()
            logger.debug(f"Item removed from cart: {variant_id}")
            return True
        return False
    
    def __iter__(self):
        """تکرار روی آیتم‌های سبد خرید"""
        variant_ids = list(self.cart.keys())
        
        # دریافت اطلاعات variants از دیتابیس
        variants = ProductVariant.objects.filter(
            id__in=variant_ids
        ).select_related('product', 'product__shop')
        
        # ایجاد مپ برای دسترسی سریع
        variant_map = {str(v.id): v for v in variants}
        
        for item_key, item_data in self.cart.items():
            variant = variant_map.get(item_key)
            
            if not variant:
                # اگر variant پیدا نشد (مثلاً حذف شده)، از سبد حذفش کن
                del self.cart[item_key]
                continue
            
            # بررسی مالکیت
            if variant.product.shop_id != self.shop.id:
                logger.warning(f"Cart contains item from different shop. Removing: {item_key}")
                del self.cart[item_key]
                continue
            
            # ایجاد آیتم برای نمایش
            item = item_data.copy()
            item['variant'] = variant
            item['product'] = variant.product
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            
            yield item
        
        # ذخیره تغییرات اگر آیتمی حذف شد
        if self.session.modified:
            self.save()
    
    def get_total_price(self):
        """محاسبه قیمت کل سبد خرید"""
        total = Decimal('0')
        for item in self:
            total += item['total_price']
        return total
    
    def get_total_items(self):
        """تعداد کل آیتم‌ها در سبد خرید"""
        return sum(item['quantity'] for item in self.cart.values())
    
    def clear(self):
        """خالی کردن سبد خرید این فروشگاه"""
        if self.cart_key in self.session:
            del self.session[self.cart_key]
            # همچنین session keys مرتبط را پاک کن
            for key in ['current_shop_id', 'current_shop_slug', 'current_shop_name']:
                if key in self.session:
                    del self.session[key]
            self.save()
            logger.debug(f"Cart cleared for shop: {self.shop.slug}")
    
    def update_quantities(self, quantities_dict):
        """
        به‌روزرسانی مقادیر چندین آیتم
        quantities_dict: {'variant_id': quantity, ...}
        """
        for variant_id_str, quantity in quantities_dict.items():
            try:
                variant_id = int(variant_id_str)
                variant = ProductVariant.objects.get(id=variant_id)
                
                # بررسی مالکیت
                if variant.product.shop_id != self.shop.id:
                    logger.warning(f"Attempt to update item from different shop: {variant_id}")
                    continue
                
                if quantity <= 0:
                    self.remove(variant_id)
                else:
                    item_key = str(variant_id)
                    if item_key in self.cart:
                        self.cart[item_key]['quantity'] = quantity
                        
            except (ValueError, ProductVariant.DoesNotExist):
                continue
        
        self.save()
    
    def validate_stock(self):
        """
        بررسی موجودی تمام آیتم‌های سبد خرید
        بازمی‌گرداند: (is_valid, error_messages)
        """
        errors = []
        
        for item in self:
            variant = item['variant']
            requested_quantity = item['quantity']
            
            if variant.stock < requested_quantity:
                errors.append(
                    f"موجودی '{variant.product.name} ({variant.color} - {variant.size})' کافی نیست. "
                    f"موجودی: {variant.stock}، درخواستی: {requested_quantity}"
                )
            
            if not variant.product.is_active:
                errors.append(
                    f"محصول '{variant.product.name}' غیرفعال شده است"
                )
        
        return len(errors) == 0, errors
    
    @property
    def is_empty(self):
        """آیا سبد خرید خالی است؟"""
        return len(self.cart) == 0
    
    def get_item_count(self, variant_id):
        """تعداد یک آیتم خاص در سبد خرید"""
        item_key = str(variant_id)
        return self.cart.get(item_key, {}).get('quantity', 0)