from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from products.models import Product
from shops.models import Shop

# --- فرم ایجاد/ویرایش محصول ---
class ProductForm(forms.ModelForm):
    # فیلدهای کمکی برای موجودی و ویژگی‌های اولیه
    initial_stock = forms.IntegerField(
        label='موجودی اولیه', 
        min_value=0, 
        required=False,  # در حالت ویرایش اجباری نیست چون از مدل خوانده می‌شود
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'تعداد'})
    )
    initial_size = forms.CharField(
        label='سایز', 
        max_length=50, 
        required=False,
        initial='Free Size',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: XL'})
    )
    initial_color = forms.CharField(
        label='رنگ', 
        max_length=50, 
        required=False,
        initial='Default',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: مشکی'})
    )
    
    # فیلدهای تصاویر
    image1 = forms.ImageField(label='تصویر اصلی', required=True, widget=forms.FileInput(attrs={'class': 'form-control'}))
    image2 = forms.ImageField(label='تصویر دوم', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    image3 = forms.ImageField(label='تصویر سوم', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    class Meta:
        model = Product
        fields = ['name', 'category', 'base_price', 'description', 'brand', 'material', 'is_active']
        
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        
        labels = {
            'base_price': 'قیمت پایه (تومان)',
            'is_active': 'انتشار محصول در فروشگاه'
        }

    def __init__(self, *args, **kwargs):
        # حذف آرگومان اضافی shop برای جلوگیری از خطا
        kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)
        
        # اگر در حالت ویرایش هستیم (محصول قبلاً ساخته شده)
        if self.instance.pk:
            # 1. خواندن موجودی کل و قرار دادن در فیلد فرم
            # (فرض بر این است که متد total_stock در مدل Product وجود دارد)
            self.fields['initial_stock'].initial = getattr(self.instance, 'total_stock', 0)
            
            # 2. پر کردن سایز و رنگ از اولین واریانت برای راحتی ویرایش
            first_variant = self.instance.variants.first()
            if first_variant:
                self.fields['initial_size'].initial = first_variant.size
                self.fields['initial_color'].initial = first_variant.color


# --- فرم ثبت نام فروشنده ---
class SellerRegisterForm(UserCreationForm):
    # ولیدیتور برای چک کردن حروف انگلیسی
    english_validator = RegexValidator(
        regex=r'^[a-zA-Z0-9_]+$',
        message='لطفاً فقط از حروف انگلیسی، اعداد و خط تیره (_) استفاده کنید.'
    )

    # بازنویسی فیلد یوزرنیم برای اعمال ولیدیتور انگلیسی
    username = forms.CharField(
        label="نام کاربری",
        validators=[english_validator],
        widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'})
    )

    shop_name = forms.CharField(
        label="نام فروشگاه (فارسی)", 
        max_length=100, 
        help_text="مثال: پوشاک شیک‌پسندان",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    shop_slug = forms.CharField(
        label="آدرس انگلیسی فروشگاه", 
        max_length=100, 
        validators=[english_validator],
        help_text="این آدرس لینک فروشگاه شما خواهد بود (مثال: shik_store)",
        widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'})
    )

    instagram_username = forms.CharField(
        label="آیدی اینستاگرام", 
        max_length=100, 
        validators=[english_validator],
        help_text="بدون @ وارد کنید",
        widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'})
    )
    
    email = forms.EmailField(
        label="ایمیل", 
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'shop_name', 'shop_slug', 'instagram_username')


# --- فرم تنظیمات فروشگاه ---
class ShopSettingsForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = [
            # اطلاعات عمومی
            'shop_name', 'instagram_username', 'bio', 'phone_number', 'address',
            # تنظیمات پرداخت
            'enable_cod', 
            'enable_card_to_card', 'card_owner_name', 'card_number', 'shaba_number',
            'enable_online_payment', 'zarinpal_merchant_id'
        ]
        widgets = {
            'shop_name': forms.TextInput(attrs={'class': 'form-control'}),
            'instagram_username': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            
            'enable_cod': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            
            'enable_card_to_card': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'card_owner_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: علی رضایی'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '۱۶ رقم روی کارت'}),
            'shaba_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IR...'}),
            
            'enable_online_payment': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'zarinpal_merchant_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'کد ۳۶ رقمی زرین‌پال'}),
        }