from django.contrib import admin
from .models import Category, Product, ProductVariant

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
    list_editable = ('is_active',) # stock حذف شد چون دیگر در این جدول نیست
    
    # اضافه کردن بخش مدیریت سایز و رنگ
    inlines = [ProductVariantInline]
    
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
        ('تصاویر', {
            'fields': ('images',)
        }),
        ('آمار', {
            'fields': ('views',),
            'classes': ('collapse',)
        }),
    )