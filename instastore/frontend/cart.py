from decimal import Decimal
from django.conf import settings
from products.models import Product, ProductVariant

class Cart:
    def __init__(self, request, shop_id=None):
        self.session = request.session
        
        # اگر shop_id پاس داده نشد، سعی می‌کنیم از سشن قبلی پیدا کنیم
        if shop_id is None:
            shop_id = self.session.get('current_shop_id')
        else:
            self.session['current_shop_id'] = shop_id
            
        self.shop_id = shop_id
        # ایجاد کلید اختصاصی برای هر فروشگاه
        self.cart_key = f'cart_{self.shop_id}' if self.shop_id else 'cart_default'
        
        cart = self.session.get(self.cart_key)
        if not cart:
            cart = self.session[self.cart_key] = {}
        self.cart = cart

    def add(self, product, variant, quantity=1, override_quantity=False):
        item_key = str(variant.id)
        if item_key not in self.cart:
            self.cart[item_key] = {
                'quantity': 0,
                'price': str(product.base_price + variant.price_adjustment),
                'product_id': product.id,
                'variant_id': variant.id
            }
        
        if override_quantity:
            self.cart[item_key]['quantity'] = quantity
        else:
            self.cart[item_key]['quantity'] += quantity
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, variant_id):
        item_key = str(variant_id)
        if item_key in self.cart:
            del self.cart[item_key]
            self.save()

    def __iter__(self):
        variant_ids = self.cart.keys()
        variants = ProductVariant.objects.filter(id__in=variant_ids).select_related('product')
        
        for variant in variants:
            item = self.cart[str(variant.id)].copy()
            item['product'] = variant.product
            item['variant'] = variant
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def get_total_items(self):
        return sum(item['quantity'] for item in self.cart.values())

    def clear(self):
        if self.cart_key in self.session:
            del self.session[self.cart_key]
            self.save()