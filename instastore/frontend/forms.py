from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from products.models import Product
from shops.models import Shop

# --- فرم ایجاد و ویرایش محصول ---
class ProductForm(forms.ModelForm):
    # فیلدهای آپلود تصویر
    image1 = forms.ImageField(label='تصویر اصلی', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    image2 = forms.ImageField(label='تصویر دوم', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    image3 = forms.ImageField(label='تصویر سوم', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    # این فیلدها برای مدیریت سمت کلاینت (JS) هستند و در متد save ویو پردازش می‌شوند
    # نیازی نیست در Meta.fields باشند، اما اینجا تعریف می‌کنیم تا در HTML رندر شوند
    # توجه: required=False می‌کنیم تا فرم جنگو گیر ندهد (چون با JS پر می‌شوند)
    
    class Meta:
        model = Product
        fields = ['name', 'category', 'base_price', 'brand', 'material', 'description', 'is_active']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'base_price': 'قیمت پایه (تومان)',
            'is_active': 'انتشار محصول'
        }

    def __init__(self, *args, **kwargs):
        self.shop = kwargs.pop('shop', None)
        super().__init__(*args, **kwargs)

# --- فرم ثبت‌نام فروشنده ---
class SellerRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label='ایمیل', widget=forms.EmailInput(attrs={'class': 'form-control', 'dir': 'ltr'}))
    shop_name = forms.CharField(max_length=100, label='نام فروشگاه', widget=forms.TextInput(attrs={'class': 'form-control'}))
    shop_slug = forms.SlugField(max_length=100, label='آدرس اینترنتی (Slug)', widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}))
    instagram_username = forms.CharField(max_length=100, required=False, label='آیدی اینستاگرام', widget=forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}))

    class Meta:
        model = User
        fields = ['username', 'email', 'shop_name', 'shop_slug', 'instagram_username']

    def clean_shop_slug(self):
        slug = self.cleaned_data['shop_slug']
        if Shop.objects.filter(slug=slug).exists():
            raise forms.ValidationError("این آدرس قبلاً انتخاب شده است.")
        return slug

# --- فرم تنظیمات فروشگاه ---
class ShopSettingsForm(forms.ModelForm):
    class Meta:
        model = Shop
        # فیلد banner حذف شد چون در مدل نیست
        fields = [
            'shop_name', 'bio', 'instagram_username', 'phone_number', 'address', 'logo',
            'enable_cod', 'enable_card_to_card', 'card_owner_name', 'card_number', 'shaba_number'
        ]
        widgets = {
            'shop_name': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'instagram_username': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            
            # تنظیمات پرداخت
            'enable_cod': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enable_card_to_card': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'card_owner_name': forms.TextInput(attrs={'class': 'form-control'}),
            'card_number': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
            'shaba_number': forms.TextInput(attrs={'class': 'form-control', 'dir': 'ltr'}),
        }