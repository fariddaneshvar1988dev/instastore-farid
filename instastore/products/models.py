from django.db import models
from django.db.models import Sum
from shops.models import Shop

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name='نام دسته‌بندی')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='شناسه در URL')
    description = models.TextField(blank=True, verbose_name='توضیحات')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    
    class Meta:
        verbose_name = 'دسته‌بندی'
        verbose_name_plural = 'دسته‌بندی‌ها'
        ordering = ['name']
    
    def __str__(self):
        return self.name

class Product(models.Model):
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='products', verbose_name='فروشگاه')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products', verbose_name='دسته‌بندی')
    
    name = models.CharField(max_length=200, verbose_name='نام محصول')
    description = models.TextField(verbose_name='توضیحات محصول')
    
    # قیمت پایه (ممکن است بسته به سایز کمی تغییر کند، اما این قیمت مبنا است)
    base_price = models.DecimalField(max_digits=12, decimal_places=0, verbose_name='قیمت پایه (ریال)')
    
    # ویژگی‌های عمومی
    brand = models.CharField(max_length=100, blank=True, verbose_name='برند')
    material = models.CharField(max_length=100, blank=True, verbose_name='جنس')

    views = models.PositiveIntegerField(default=0, verbose_name='تعداد بازدید')
    
    is_active = models.BooleanField(default=True, verbose_name='فعال/غیرفعال')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخرین بروزرسانی')
    def __str__(self):
        return f"{self.name} - {self.shop.shop_name}"

    class Meta:
        verbose_name = 'محصول'
        verbose_name_plural = 'محصولات'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['shop', 'is_active']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.shop.shop_name}"
    
    @property
    def main_image(self):
        first_image = self.images.first() # توجه: اینجا images اشاره به مدل جدید دارد (related_name)
        if first_image:
            return first_image.image.url
        return None
    
    @property
    def price(self):
        """برای سازگاری با تمپلیت‌هایی که از .price استفاده می‌کنند"""
        return self.base_price

    def get_price_in_toman(self):
        return self.base_price / 10
    
    @property
    def total_stock(self):
        """مجموع موجودی تمام سایزها و رنگ‌ها"""
        # اگر واریانتی تعریف نشده باشد، 0 برمی‌گرداند
        return self.variants.aggregate(total=Sum('stock'))['total'] or 0
    
    @property
    def is_available(self):
        """محصول موجود است اگر حداقل یک واریانت موجودی داشته باشد"""
        return self.total_stock > 0 and self.is_active
    
    @property
    def available_colors(self):
        """لیست رنگ‌های موجود برای فیلتر"""
        return self.variants.filter(stock__gt=0).values_list('color', flat=True).distinct()


class ProductVariant(models.Model):
    """
    مدل تنوع محصول: هر ردیف مشخص می‌کند از یک رنگ و سایز خاص چقدر داریم.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants', verbose_name='محصول')
    
    size = models.CharField(max_length=50, verbose_name='سایز')     # مثال: XL, 42
    color = models.CharField(max_length=50, verbose_name='رنگ')    # مثال: قرمز, مشکی
    
    stock = models.PositiveIntegerField(default=0, verbose_name='موجودی انبار')
    
    # اگر سایز خاصی گران‌تر است (مثلاً سایز 5XL)، این مبلغ به قیمت پایه اضافه می‌شود
    price_adjustment = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='افزایش قیمت (ریال)')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'تنوع (رنگ/سایز)'
        verbose_name_plural = 'تنوع‌های محصول'
        # جلوگیری از تعریف تکراری یک رنگ و سایز برای یک محصول
        unique_together = ('product', 'size', 'color')

    def __str__(self):
        return f"{self.product.name} ({self.color} - {self.size})"

    @property
    def final_price(self):
        """قیمت نهایی این واریانت"""
        return self.product.base_price + self.price_adjustment

    def decrease_stock(self, quantity):
        """کسر موجودی از این واریانت خاص"""
        if self.stock >= quantity:
            self.stock = models.F('stock') - quantity
            self.save()
            self.refresh_from_db()
            return True
        return False
    
    
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images', verbose_name='محصول')
    image = models.ImageField(upload_to='products/%Y/%m/', verbose_name='تصویر')
    alt_text = models.CharField(max_length=200, blank=True, null=True, verbose_name='متن جایگزین')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'تصویر محصول'
        verbose_name_plural = 'تصاویر محصول'