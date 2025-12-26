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

    def add(self, product_id, quantity=1, size='Free Size', color='Default'):
        """
        محصول را به سبد اضافه می‌کند.
        """
        product_id = str(product_id)
        cart_key = f"{product_id}-{size}-{color}"

        if cart_key not in self.cart:
            self.cart[cart_key] = {
                'product_id': product_id,
                'quantity': 0,
                'size': size,
                'color': color,
                'price': 0 
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
        اطلاعات کامل محصول را از دیتابیس می‌گیرد و قیمت را محاسبه می‌کند.
        """
        product_ids = [item['product_id'] for item in self.cart.values()]
        products = Product.objects.filter(id__in=product_ids)
        product_map = {str(p.id): p for p in products}

        for key, item in self.cart.items():
            product = product_map.get(item['product_id'])
            if product:
                item['product'] = product
                # پیدا کردن قیمت دقیق واریانت
                variant = ProductVariant.objects.filter(
                    product=product,
                    size=item['size'],
                    color=item['color']
                ).first()
                
                # قیمت نهایی (اگر واریانت بود قیمت آن، وگرنه قیمت پایه)
                price = variant.final_price if variant else product.base_price
                
                item['price'] = int(price)
                item['total_price'] = item['price'] * item['quantity']
                item['cart_key'] = key
                item['variant_id'] = variant.id if variant else None
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