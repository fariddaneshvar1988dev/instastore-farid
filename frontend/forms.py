from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from products.models import Product

class ProductForm(forms.ModelForm):
    # این فیلدها در مدل نیستند اما برای راحتی کاربر در فرم قرار می‌دهیم
    # تا در لحظه ساخت محصول، یک واریانت اولیه (رنگ و سایز) هم ساخته شود
    initial_stock = forms.IntegerField(
        label='موجودی اولیه', 
        min_value=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    initial_size = forms.CharField(
        label='سایز', 
        max_length=50, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    initial_color = forms.CharField(
        label='رنگ', 
        max_length=50, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    # فیلدهای تصاویر
    image1 = forms.ImageField(label='تصویر اصلی', required=False)
    image2 = forms.ImageField(label='تصویر دوم', required=False)
    image3 = forms.ImageField(label='تصویر سوم', required=False)

    class Meta:
        model = Product
        # نام فیلد قیمت در مدل جدید base_price است
        fields = ['name', 'category', 'base_price', 'description', 
                  'brand', 'material', 'is_active']
        
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
            'is_active': 'محصول فعال است'
        }

    def __init__(self, *args, **kwargs):
        shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)

class SellerRegisterForm(UserCreationForm):
    shop_name = forms.CharField(
        label="نام فروشگاه", 
        max_length=100, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    instagram_username = forms.CharField(
        label="آیدی اینستاگرام", 
        max_length=100, 
        help_text="بدون @ وارد کنید",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'my_shop_id'})
    )
    email = forms.EmailField(
        label="ایمیل", 
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)



from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from products.models import Product

# ... (ProductForm بدون تغییر بماند) ...
class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(label='موجودی اولیه', min_value=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    initial_size = forms.CharField(label='سایز', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    initial_color = forms.CharField(label='رنگ', max_length=50, widget=forms.TextInput(attrs={'class': 'form-control'}))
    image1 = forms.ImageField(label='تصویر اصلی', required=False)
    image2 = forms.ImageField(label='تصویر دوم', required=False)
    image3 = forms.ImageField(label='تصویر سوم', required=False)

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
            'is_active': 'محصول فعال است'
        }

    def __init__(self, *args, **kwargs):
        shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)

class SellerRegisterForm(UserCreationForm):
    # ولیدیتور برای چک کردن حروف انگلیسی
    english_validator = RegexValidator(
        regex=r'^[a-zA-Z0-9_]+$',
        message='لطفاً فقط از حروف انگلیسی، اعداد و خط تیره (_) استفاده کنید. حروف فارسی مجاز نیست.'
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
    
    # فیلد جدید برای آدرس انگلیسی
    shop_slug = forms.CharField(
        label="آدرس انگلیسی فروشگاه", 
        max_length=100, 
        validators=[english_validator],
        help_text="این آدرس لینک فروشگاه شما خواهد بود (مثال: shik_pasandan)",
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














# در انتهای فایل instastore/frontend/forms.py اضافه کنید:

from shops.models import Shop  # اگر ایمپورت نشده، اضافه کنید

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