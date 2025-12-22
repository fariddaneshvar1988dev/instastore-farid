from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Category, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'price', 'stock', 'is_available', 'created_at')
    list_filter = ('is_available', 'category', 'created_at')
    search_fields = ('name', 'description', 'shop__shop_name')
    readonly_fields = ('views', 'created_at', 'updated_at')
    list_editable = ('price', 'stock', 'is_available')
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('shop', 'name', 'description', 'price', 'category')
        }),
        ('موجودی و وضعیت', {
            'fields': ('stock', 'is_available')
        }),
        ('ویژگی‌های محصول', {
            'fields': ('size', 'color', 'brand', 'material'),
            'classes': ('collapse',)
        }),
        ('تصاویر', {
            'fields': ('images',)
        }),
        ('آمار', {
            'fields': ('views',),
            'classes': ('collapse',)
        }),
        ('تاریخ‌ها', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )