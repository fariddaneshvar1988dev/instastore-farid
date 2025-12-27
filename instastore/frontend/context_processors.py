def cart_context(request):
    """Context processor برای نمایش تعداد آیتم‌های سبد خرید"""
    # خواندن سبد خرید از سشن
    cart = request.session.get('cart', [])
    return {
        'cart_count': len(cart),  # نام متغیر باید با cart_badge.html یکی باشد
    }