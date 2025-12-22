# frontend/context_processors.py
def cart_context(request):
    """Context processor برای نمایش سبد خرید در همه صفحات"""
    # فعلاً مقدار ثابت برمی‌گردانیم
    # بعداً با session یا دیتابیس پیاده‌سازی می‌کنیم
    return {
        'cart_items_count': 0,
    }