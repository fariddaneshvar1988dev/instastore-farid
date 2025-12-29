from django.contrib import admin
from .models import Category, Product, ProductVariant, ProductImage

# ۱. مدیریت تصاویر به صورت Inline (داخل صفحه محصول)
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1  # یک ردیف خالی برای آپلود عکس جدید نشان می‌دهد
    fields = ('image', 'alt_text')
    verbose_name = "تصویر محصول"
    verbose_name_plural = "گالری تصاویر"

# ۲. مدیریت تنوع (سایز/رنگ)
class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1
    fields = ('size', 'color', 'stock', 'price_adjustment')
    verbose_name = "تنوع (رنگ/سایز)"
    verbose_name_plural = "تنوع‌های محصول"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'base_price', 'total_stock', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('name', 'description', 'shop__shop_name')
    readonly_fields = ('views', 'created_at', 'updated_at')
    list_editable = ('is_active',)
    
    # اضافه کردن هر دو Inline (تنوع + تصاویر) به صفحه محصول
    inlines = [ProductVariantInline, ProductImageInline]
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('shop', 'name', 'description', 'base_price', 'category')
        }),
        ('وضعیت', {
            'fields': ('is_active',)
        }),
        ('ویژگی‌های عمومی', {
            'fields': ('brand', 'material'),
            'classes': ('collapse',)
        }),
        # نکته مهم: بخش "تصاویر" را از اینجا حذف کردیم چون الان پایین صفحه به صورت Inline می‌آید
        ('آمار', {
            'fields': ('views',),
            'classes': ('collapse',)
        }),
    )