from django import forms
from django.contrib.auth.models import User
from shops.models import Shop
from products.models import Product

class SellerRegisterForm(forms.ModelForm):
    shop_name = forms.CharField(label="نام فروشگاه", widget=forms.TextInput(attrs={'class': 'form-control'}))
    shop_slug = forms.SlugField(label="آدرس اینترنتی (Slug)", required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'مثال: my-shop'}))
    instagram_username = forms.CharField(label="آیدی اینستاگرام", widget=forms.TextInput(attrs={'class': 'form-control'}))
    password = forms.CharField(label="رمز عبور", widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    confirm_password = forms.CharField(label="تکرار رمز عبور", widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean_instagram_username(self):
        """چک کردن یکتا بودن نام کاربری (آیدی اینستاگرام)"""
        username = self.cleaned_data.get('instagram_username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("این آیدی اینستاگرام قبلاً ثبت نام کرده است.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("رمز عبور و تکرار آن یکسان نیستند.")
        return cleaned_data


class ProductForm(forms.ModelForm):
    # === فیلدهای اختصاصی که در مدل Product نیستند اما برای واریانت لازم‌اند ===
    initial_stock = forms.IntegerField(
        label='موجودی انبار', 
        min_value=0, 
        required=True, 
        help_text='برای نمایش در سایت، حداقل ۱ عدد وارد کنید.',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'تعداد'})
    )
    initial_size = forms.CharField(
        label='سایز', 
        required=True, 
        initial='Free Size',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    initial_color = forms.CharField(
        label='رنگ', 
        required=True, 
        initial='Default',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    # ======================================================================

    image1 = forms.ImageField(label='تصویر ۱', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    image2 = forms.ImageField(label='تصویر ۲', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))
    image3 = forms.ImageField(label='تصویر ۳', required=False, widget=forms.FileInput(attrs={'class': 'form-control'}))

    def __init__(self, *args, **kwargs):
        self.shop = kwargs.pop('shop', None)
        super(ProductForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Product
        fields = [
            'name', 'category', 'base_price', 'brand', 'material', 'description', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'base_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ShopSettingsForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = [
            'shop_name', 'instagram_username', 'bio', 'phone_number', 'address',
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