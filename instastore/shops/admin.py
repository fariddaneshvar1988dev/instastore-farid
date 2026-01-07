from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse
import csv
from datetime import timedelta
from .models import Plan, Shop
from logs.models import AdminLog


# فیلترهای سفارشی
class SubscriptionStatusFilter(admin.SimpleListFilter):
    """فیلتر وضعیت اشتراک"""
    title = 'وضعیت اشتراک'
    parameter_name = 'subscription_status'

    def lookups(self, request, model_admin):
        return [
            ('active', 'فعال'),
            ('expired', 'منقضی شده'),
            ('no_plan', 'بدون پلن'),
            ('expiring_soon', 'در حال انقضا (کمتر از ۷ روز)'),
        ]

    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'active':
            return queryset.filter(
                current_plan__isnull=False,
                plan_expires_at__gt=now,
                is_active=True
            )
        elif self.value() == 'expired':
            return queryset.filter(
                current_plan__isnull=False,
                plan_expires_at__lte=now,
                is_active=True
            )
        elif self.value() == 'no_plan':
            return queryset.filter(current_plan__isnull=True, is_active=True)
        elif self.value() == 'expiring_soon':
            return queryset.filter(
                current_plan__isnull=False,
                plan_expires_at__gt=now,
                plan_expires_at__lte=now + timedelta(days=7),
                is_active=True
            )
        return queryset


class PlanFilter(admin.SimpleListFilter):
    """فیلتر بر اساس پلن"""
    title = 'پلن'
    parameter_name = 'plan'

    def lookups(self, request, model_admin):
        plans = Plan.objects.filter(is_active=True).values_list('id', 'name')
        return [(str(id), name) for id, name in plans]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(current_plan_id=self.value())
        return queryset


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    """مدیریت پلن‌های اشتراک"""
    list_display = (
        'name', 'code', 'get_display_days', 'price_formatted', 
        'max_products', 'max_orders_per_month', 'is_active', 
        'is_default', 'shop_count', 'sort_order'
    )
    
    list_filter = ('is_active', 'code', 'is_default')
    search_fields = ('name', 'code', 'description')
    ordering = ('sort_order', 'price')
    
    list_editable = ('is_active', 'is_default', 'sort_order', 'max_products', 'max_orders_per_month')
    
    fieldsets = (
        ('اطلاعات اصلی', {
            'fields': ('code', 'name', 'description', 'sort_order')
        }),
        ('قیمت و مدت', {
            'fields': ('price', 'days', 'get_display_days')
        }),
        ('محدودیت‌ها', {
            'fields': ('max_products', 'max_orders_per_month')
        }),
        ('تنظیمات نمایش', {
            'fields': ('is_active', 'is_default', 'is_popular')
        }),
        ('آمار', {
            'fields': ('shop_count', 'created_info'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('get_display_days', 'shop_count', 'created_info')
    
    # Actions
    actions = ['activate_plans', 'deactivate_plans', 'set_as_default', 'export_plans_csv']
    
    def price_formatted(self, obj):
        """قیمت فرمت شده"""
        if obj.price == 0:
            return format_html('<span class="badge bg-success">رایگان</span>')
        return f"{obj.price:,} تومان"
    price_formatted.short_description = 'قیمت'
    
    def get_display_days(self, obj):
        """نمایش مدت زمان به صورت خوانا"""
        if obj.days >= 30:
            months = obj.days // 30
            return f"{months} ماه"
        return f"{obj.days} روز"
    get_display_days.short_description = 'مدت زمان'
    
    def shop_count(self, obj):
        """تعداد فروشگاه‌های استفاده کننده"""
        count = obj.shops.count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    shop_count.short_description = 'تعداد فروشگاه‌ها'
    
    def created_info(self, obj):
        """اطلاعات ایجاد"""
        return f"ایجاد شده در: {obj.created_at.strftime('%Y/%m/%d')}"
    created_info.short_description = 'اطلاعات'
    
    # Custom Actions
    def activate_plans(self, request, queryset):
        """فعال کردن پلن‌های انتخاب شده"""
        updated = queryset.update(is_active=True)
        self.log_admin_action(request, f"فعال کردن {updated} پلن")
        messages.success(request, f'{updated} پلن فعال شدند')
    activate_plans.short_description = "فعال کردن پلن‌های انتخاب شده"
    
    def deactivate_plans(self, request, queryset):
        """غیرفعال کردن پلن‌های انتخاب شده"""
        updated = queryset.update(is_active=False)
        self.log_admin_action(request, f"غیرفعال کردن {updated} پلن")
        messages.success(request, f'{updated} پلن غیرفعال شدند')
    deactivate_plans.short_description = "غیرفعال کردن پلن‌های انتخاب شده"
    
    def set_as_default(self, request, queryset):
        """تنظیم به عنوان پیش‌فرض"""
        # اول همه را غیرپیش‌فرض کن
        Plan.objects.update(is_default=False)
        
        # فقط اولی را پیش‌فرض کن
        if queryset.exists():
            plan = queryset.first()
            plan.is_default = True
            plan.save()
            
            self.log_admin_action(request, f"تنظیم پلن {plan.name} به عنوان پیش‌فرض")
            messages.success(request, f'پلن "{plan.name}" به عنوان پیش‌فرض تنظیم شد')
    set_as_default.short_description = "تنظیم به عنوان پلن پیش‌فرض"
    
    def export_plans_csv(self, request, queryset):
        """اکسپورت به CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="plans.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['نام', 'کد', 'قیمت', 'روزها', 'حداکثر محصول', 'حداکثر سفارش', 'وضعیت'])
        
        for plan in queryset:
            writer.writerow([
                plan.name,
                plan.code,
                plan.price,
                plan.days,
                plan.max_products,
                plan.max_orders_per_month,
                'فعال' if plan.is_active else 'غیرفعال'
            ])
        
        self.log_admin_action(request, f"اکسپورت {queryset.count()} پلن به CSV")
        return response
    export_plans_csv.short_description = "اکسپورت به CSV"
    
    def log_admin_action(self, request, action):
        """ثبت لاگ فعالیت ادمین"""
        if hasattr(request, 'user'):
            AdminLog.objects.create(
                admin=request.user,
                action=action,
                model='Plan',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
    
    def get_client_ip(self, request):
        """دریافت IP کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """مدیریت فروشگاه‌ها"""
    list_display = (
        'shop_name', 'instagram_username', 'user_email',
        'current_plan_display', 'plan_status_badge', 'remaining_days_display',
        'subscription_progress', 'product_count', 'order_count_month',
        'is_active_badge', 'created_at_formatted', 'admin_actions'
    )
    
    list_filter = (
        'is_active', 
        SubscriptionStatusFilter,
        PlanFilter,
        'created_at',
        'enable_cod',
        'enable_online_payment',
    )
    
    search_fields = (
        'shop_name', 'instagram_username', 
        'user__username', 'user__email', 'user__first_name', 'user__last_name',
        'phone_number', 'address', 'slug'
    )
    
    list_select_related = ('user', 'current_plan')
    
    # 🔥 مهم: تاریخ‌های پلن قابل ویرایش هستند
    readonly_fields = ('slug', 'created_at', 'updated_at', 'debug_info', 'stats_info')
    
    # Actions برای مدیریت دسته‌ای
    actions = [
        'activate_shops',
        'deactivate_shops',
        'extend_subscription_30_days',
        'extend_subscription_90_days',
        'assign_free_plan',
        'assign_basic_plan',
        'assign_pro_plan',
        'export_shops_csv',
        'send_welcome_email',
        'send_expiry_warning',
    ]
    
    # فیلدهای قابل ویرایش
    fieldsets = (
        ('اطلاعات پایه', {
            'fields': (
                'user', 'shop_name', 'slug', 'instagram_username',
                'bio', 'phone_number', 'address', 'logo', 'is_active'
            )
        }),
        ('تنظیمات پرداخت', {
            'fields': (
                'enable_cod', 'enable_card_to_card', 'card_owner_name',
                'card_number', 'shaba_number', 'enable_online_payment',
                'zarinpal_merchant_id'
            ),
            'classes': ('collapse',)
        }),
        ('🔥 مدیریت اشتراک (قابل ویرایش توسط ادمین)', {
            'fields': (
                'current_plan', 
                'plan_started_at',  # قابل ویرایش
                'plan_expires_at',  # قابل ویرایش
            ),
            'description': 'می‌توانید پلن و تاریخ‌های اشتراک را مستقیماً تغییر دهید'
        }),
        ('آمار و اطلاعات', {
            'fields': ('stats_info', 'debug_info', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # تغییر فرم برای نمایش بهتر
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # محدود کردن انتخاب پلن به پلن‌های فعال
        if 'current_plan' in form.base_fields:
            form.base_fields['current_plan'].queryset = Plan.objects.filter(is_active=True)
            form.base_fields['current_plan'].empty_label = "--- انتخاب کنید ---"
        
        return form
    
    # ستون‌های سفارشی
    def user_email(self, obj):
        """ایمیل کاربر"""
        if obj.user and obj.user.email:
            return obj.user.email
        return "-"
    user_email.short_description = 'ایمیل'
    user_email.admin_order_field = 'user__email'
    
    def current_plan_display(self, obj):
        """نمایش پلن"""
        if obj.current_plan:
            return format_html(
                '<strong>{}</strong><br><small>{}</small>',
                obj.current_plan.name,
                obj.current_plan.get_display_days()
            )
        return format_html('<span class="badge bg-secondary">بدون پلن</span>')
    current_plan_display.short_description = 'پلن'
    
    def plan_status_badge(self, obj):
        """نمایش وضعیت اشتراک با Badge"""
        if not obj.current_plan:
            return format_html('<span class="badge bg-secondary">بدون پلن</span>')
        
        status = obj.subscription_status
        color = obj.subscription_status_color
        
        badge_class = f'badge bg-{color}'
        
        if status == 'فعال':
            return format_html(
                '<span class="{}">{} ({} روز)</span>',
                badge_class, status, obj.remaining_days
            )
        else:
            return format_html('<span class="{}">{}</span>', badge_class, status)
    plan_status_badge.short_description = 'وضعیت اشتراک'
    plan_status_badge.admin_order_field = 'plan_expires_at'
    
    def remaining_days_display(self, obj):
        """نمایش روزهای باقی‌مانده"""
        if not obj.current_plan or not obj.plan_expires_at:
            return "-"
        
        days = obj.remaining_days
        
        if days > 30:
            color = 'success'
            icon = '✓'
        elif days > 7:
            color = 'warning'
            icon = '⚠'
        else:
            color = 'danger'
            icon = '⏰'
        
        return format_html(
            '<span class="badge bg-{}" style="font-size: 0.9em;">{} {} روز</span>',
            color, icon, days
        )
    remaining_days_display.short_description = 'روزهای باقی‌مانده'
    remaining_days_display.admin_order_field = 'plan_expires_at'
    
    def subscription_progress(self, obj):
        """نمودار پیشرفت اشتراک"""
        if not obj.current_plan or not obj.plan_expires_at:
            return "-"
        
        percent = obj.remaining_days_percent
        color = 'success' if percent > 50 else 'warning' if percent > 20 else 'danger'
        
        return format_html(
            '''
            <div style="width: 100px; background: #eee; border-radius: 3px;">
                <div style="width: {}%; height: 20px; background: var(--bs-{}); 
                         border-radius: 3px; text-align: center; color: white; 
                         font-size: 11px; line-height: 20px;">
                    {}%
                </div>
            </div>
            ''',
            percent, color, percent
        )
    subscription_progress.short_description = 'پیشرفت'
    
    def product_count(self, obj):
        """تعداد محصولات"""
        count = obj.products.filter(is_active=True).count()
        return format_html('<span class="badge bg-info">{}</span>', count)
    product_count.short_description = 'محصولات'
    
    def order_count_month(self, obj):
        """تعداد سفارشات در ماه جاری"""
        from datetime import datetime
        current_month = datetime.now().month
        current_year = datetime.now().year
        count = obj.orders.filter(
            created_at__month=current_month,
            created_at__year=current_year
        ).count()
        
        if obj.current_plan:
            max_orders = obj.current_plan.max_orders_per_month
            percent = int((count / max_orders) * 100) if max_orders > 0 else 0
            
            color = 'success' if percent < 80 else 'warning' if percent < 100 else 'danger'
            
            return format_html(
                '<span class="badge bg-{}">{} / {}</span>',
                color, count, max_orders
            )
        
        return format_html('<span class="badge bg-secondary">{}</span>', count)
    order_count_month.short_description = 'سفارشات (ماه)'
    
    def is_active_badge(self, obj):
        """نمایش وضعیت فعال/غیرفعال"""
        if obj.is_active:
            return format_html('<span class="badge bg-success">فعال</span>')
        return format_html('<span class="badge bg-danger">غیرفعال</span>')
    is_active_badge.short_description = 'وضعیت'
    is_active_badge.admin_order_field = 'is_active'
    
    def created_at_formatted(self, obj):
        """تاریخ ایجاد فرمت شده"""
        if obj.created_at:
            return obj.created_at.strftime('%Y/%m/%d')
        return "-"
    created_at_formatted.short_description = 'تاریخ ایجاد'
    created_at_formatted.admin_order_field = 'created_at'
    
    def admin_actions(self, obj):
        """عملیات مدیریتی"""
        links = []
        
        # مشاهده فروشگاه
        links.append(
            f'<a href="/shop/{obj.slug}/" target="_blank" class="btn btn-xs btn-info" title="مشاهده فروشگاه">👁️</a>'
        )
        
        # تمدید اشتراک
        if obj.current_plan:
            links.append(
                f'<a href="{reverse("admin:shops_shop_changelist")}extend/{obj.id}/" class="btn btn-xs btn-warning" title="تمدید اشتراک">⏱️</a>'
            )
        
        # ارسال پیام
        links.append(
            f'<a href="mailto:{obj.user.email if obj.user and obj.user.email else "#"}" class="btn btn-xs btn-primary" title="ارسال ایمیل">✉️</a>'
        )
        
        return format_html(' '.join(links))
    admin_actions.short_description = 'عملیات'
    
    # فیلدهای فقط خواندنی
    def debug_info(self, obj):
        """اطلاعات دیباگ"""
        return format_html('<pre style="font-size: 11px;">{}</pre>', obj.debug_info())
    debug_info.short_description = 'اطلاعات دیباگ'
    
    def stats_info(self, obj):
        """آمار فروشگاه"""
        stats = obj.get_usage_stats()
        
        html = f"""
        <div style="font-size: 12px;">
            <strong>📊 آمار استفاده از پلن:</strong><br>
            <div style="margin-left: 10px;">
                📦 محصولات: {stats['products']['current']} / {stats['products']['max']} (مانده: {stats['products']['remaining']})<br>
                🛒 سفارشات (ماه): {stats['orders']['current']} / {stats['orders']['max']} (مانده: {stats['orders']['remaining']})
            </div>
        </div>
        """
        return format_html(html)
    stats_info.short_description = 'آمار'
    
    # Custom Actions
    def activate_shops(self, request, queryset):
        """فعال کردن فروشگاه‌های انتخاب شده"""
        updated = queryset.update(is_active=True)
        self.log_admin_action(request, f"فعال کردن {updated} فروشگاه")
        messages.success(request, f'{updated} فروشگاه فعال شدند')
    activate_shops.short_description = "فعال کردن فروشگاه‌ها"
    
    def deactivate_shops(self, request, queryset):
        """غیرفعال کردن فروشگاه‌های انتخاب شده"""
        updated = queryset.update(is_active=False)
        self.log_admin_action(request, f"غیرفعال کردن {updated} فروشگاه")
        messages.success(request, f'{updated} فروشگاه غیرفعال شدند')
    deactivate_shops.short_description = "غیرفعال کردن فروشگاه‌ها"
    
    def extend_subscription_30_days(self, request, queryset):
        """تمدید 30 روزه اشتراک"""
        updated = 0
        for shop in queryset:
            if shop.extend_subscription(30):
                updated += 1
        
        self.log_admin_action(request, f"تمدید 30 روزه {updated} فروشگاه")
        messages.success(request, f'{updated} فروشگاه به مدت 30 روز تمدید شدند')
    extend_subscription_30_days.short_description = "تمدید 30 روزه"
    
    def extend_subscription_90_days(self, request, queryset):
        """تمدید 90 روزه اشتراک"""
        updated = 0
        for shop in queryset:
            if shop.extend_subscription(90):
                updated += 1
        
        self.log_admin_action(request, f"تمدید 90 روزه {updated} فروشگاه")
        messages.success(request, f'{updated} فروشگاه به مدت 90 روز تمدید شدند')
    extend_subscription_90_days.short_description = "تمدید 90 روزه"
    
    def assign_free_plan(self, request, queryset):
        """اختصاص پلن رایگان"""
        free_plan = Plan.objects.filter(code='free', is_active=True).first()
        if not free_plan:
            messages.error(request, "پلن رایگان یافت نشد")
            return
        
        updated = 0
        for shop in queryset:
            shop.renew_subscription(free_plan, start_from_now=True)
            updated += 1
        
        self.log_admin_action(request, f"اختصاص پلن رایگان به {updated} فروشگاه")
        messages.success(request, f'پلن رایگان به {updated} فروشگاه اختصاص یافت')
    assign_free_plan.short_description = "اختصاص پلن رایگان"
    
    def assign_basic_plan(self, request, queryset):
        """اختصاص پلن پایه"""
        basic_plan = Plan.objects.filter(code='basic', is_active=True).first()
        if not basic_plan:
            messages.error(request, "پلن پایه یافت نشد")
            return
        
        updated = 0
        for shop in queryset:
            shop.renew_subscription(basic_plan, start_from_now=True)
            updated += 1
        
        self.log_admin_action(request, f"اختصاص پلن پایه به {updated} فروشگاه")
        messages.success(request, f'پلن پایه به {updated} فروشگاه اختصاص یافت')
    assign_basic_plan.short_description = "اختصاص پلن پایه"
    
    def assign_pro_plan(self, request, queryset):
        """اختصاص پلن حرفه‌ای"""
        pro_plan = Plan.objects.filter(code='pro', is_active=True).first()
        if not pro_plan:
            messages.error(request, "پلن حرفه‌ای یافت نشد")
            return
        
        updated = 0
        for shop in queryset:
            shop.renew_subscription(pro_plan, start_from_now=True)
            updated += 1
        
        self.log_admin_action(request, f"اختصاص پلن حرفه‌ای به {updated} فروشگاه")
        messages.success(request, f'پلن حرفه‌ای به {updated} فروشگاه اختصاص یافت')
    assign_pro_plan.short_description = "اختصاص پلن حرفه‌ای"
    
    def export_shops_csv(self, request, queryset):
        """اکسپورت فروشگاه‌ها به CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="shops.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'نام فروشگاه', 'آدرس اینستاگرام', 'ایمیل', 'پلن',
            'شروع اشتراک', 'انقضای اشتراک', 'روزهای باقی‌مانده',
            'وضعیت', 'تاریخ ایجاد', 'تلفن'
        ])
        
        for shop in queryset.select_related('user', 'current_plan'):
            writer.writerow([
                shop.shop_name,
                shop.instagram_username,
                shop.user.email if shop.user else '',
                shop.current_plan.name if shop.current_plan else '',
                shop.plan_started_at.strftime('%Y/%m/%d') if shop.plan_started_at else '',
                shop.plan_expires_at.strftime('%Y/%m/%d') if shop.plan_expires_at else '',
                shop.remaining_days,
                'فعال' if shop.is_active else 'غیرفعال',
                shop.created_at.strftime('%Y/%m/%d'),
                shop.phone_number
            ])
        
        self.log_admin_action(request, f"اکسپورت {queryset.count()} فروشگاه به CSV")
        return response
    export_shops_csv.short_description = "اکسپورت به CSV"
    
    def send_welcome_email(self, request, queryset):
        """ارسال ایمیل خوش‌آمدگویی"""
        # اینجا منطق ارسال ایمیل قرار می‌گیرد
        count = queryset.count()
        self.log_admin_action(request, f"ارسال ایمیل خوش‌آمد به {count} فروشگاه")
        messages.info(request, f'ایمیل خوش‌آمدگویی برای {count} فروشگاه آماده ارسال است')
    send_welcome_email.short_description = "ارسال ایمیل خوش‌آمدگویی"
    
    def send_expiry_warning(self, request, queryset):
        """ارسال هشدار انقضا"""
        shops = queryset.filter(
            current_plan__isnull=False,
            plan_expires_at__isnull=False,
            plan_expires_at__gt=timezone.now(),
            plan_expires_at__lte=timezone.now() + timedelta(days=7)
        )
        
        count = shops.count()
        self.log_admin_action(request, f"ارسال هشدار انقضا به {count} فروشگاه")
        messages.info(request, f'هشدار انقضا برای {count} فروشگاه آماده ارسال است')
    send_expiry_warning.short_description = "ارسال هشدار انقضا"
    
    # تغییر view مربوطه
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """نمایش صفحه ویرایش"""
        extra_context = extra_context or {}
        extra_context['title'] = 'ویرایش فروشگاه - مدیریت کامل اشتراک'
        return super().change_view(request, object_id, form_url, extra_context)
    
    def get_queryset(self, request):
        """بهینه‌سازی کوئری‌ست"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'current_plan').prefetch_related('products', 'orders')
    
    def log_admin_action(self, request, action):
        """ثبت لاگ فعالیت ادمین"""
        if hasattr(request, 'user'):
            AdminLog.objects.create(
                admin=request.user,
                action=action,
                model='Shop',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
    
    def get_client_ip(self, request):
        """دریافت IP کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip