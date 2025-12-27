from decimal import Decimal
from products.models import Product, ProductVariant

class Cart:
    def __init__(self, request):
        """
        سبد خرید را مقداردهی اولیه می‌کند.
        """
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            # ذخیره یک سبد خالی در سشن
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product, variant, quantity=1):
        """
        محصول را به سبد اضافه می‌کند.
        توجه: فقط داده‌های متنی و عددی ذخیره می‌شوند، نه آبجکت‌ها.
        """
        product_id = str(product.id)
        variant_id = str(variant.id)
        
        # کلید یکتا برای هر ترکیب محصول و واریانت
        cart_key = f"{product_id}-{variant_id}"

        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'product_id': product_id,
                'variant_id': variant_id,
                'quantity': 0,
                # قیمت را به int یا float تبدیل می‌کنیم
                'price': int(product.base_price + variant.price_adjustment),
                'size': variant.size,
                'color': variant.color,
                # آدرس عکس را به عنوان رشته ذخیره می‌کنیم
                'image': str(product.images[0]) if product.images else '',
            }
        
        self.cart[cart_key]['quantity'] += quantity
        self.save()

    def remove(self, cart_key):
        """حذف آیتم از سبد"""
        if cart_key in self.cart:
            del self.cart[cart_key]
            self.save()

    def save(self):
        self.session.modified = True

    def __iter__(self):
        """
        اطلاعات کامل محصول را از دیتابیس می‌گیرد و برای نمایش آماده می‌کند.
        """
        product_ids = [item['product_id'] for item in self.cart.values()]
        products = Product.objects.filter(id__in=product_ids)
        product_map = {str(p.id): p for p in products}

        for key, item in self.cart.items():
            # *** تغییر حیاتی ***
            # ما از item.copy() استفاده می‌کنیم تا دیکشنری اصلی داخل سشن دستکاری نشود.
            # اگر کپی نگیریم، آبجکت product وارد سشن شده و خطای JSON می‌دهد.
            item = item.copy()
            
            product = product_map.get(item['product_id'])
            if product:
                item['product'] = product
                item['total_price'] = item['price'] * item['quantity']
                item['cart_key'] = key
                yield item

    def get_total_price(self):
        """جمع کل مبلغ سبد"""
        return sum(item['total_price'] for item in self.__iter__())

    def get_total_items(self):
        """تعداد کل آیتم‌ها"""
        return sum(item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session['cart']
        self.save()