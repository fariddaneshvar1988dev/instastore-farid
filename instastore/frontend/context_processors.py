def cart_context(request):
    """Context processor برای نمایش تعداد آیتم‌های سبد خرید"""
    cart_count = 0
    cart_total = 0
    
    try:
        # اگر shop در request است، سبد خرید آن را بگیر
        if hasattr(request, 'shop') and request.shop:
            from .cart import Cart
            try:
                cart = Cart(request, shop=request.shop)
                cart_count = cart.get_total_items()
                cart_total = float(cart.get_total_price())
            except (ValueError, Exception) as e:
                # اگر خطایی پیش آمد، سبد خرید خالی در نظر بگیر
                pass
    except:
        pass
    
    return {
        'cart_count': cart_count,
        'cart_total': cart_total,
        'current_shop': getattr(request, 'shop', None),
    }