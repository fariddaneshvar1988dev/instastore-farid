from django.db import models

# Create your models here.
"""
سیستم لاگ‌گیری کامل برای پلتفرم
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import uuid

class AdminLog(models.Model):
    """
    لاگ تمام فعالیت‌های ادمین‌های پلتفرم
    """
    ACTION_TYPES = [
        ('CREATE', 'ایجاد'),
        ('UPDATE', 'ویرایش'),
        ('DELETE', 'حذف'),
        ('LOGIN', 'ورود'),
        ('LOGOUT', 'خروج'),
        ('EXPORT', 'اکسپورت'),
        ('IMPORT', 'ایمپورت'),
        ('ACTION', 'عملیات'),
        ('ERROR', 'خطا'),
        ('WARNING', 'هشدار'),
        ('INFO', 'اطلاعات'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='admin_logs',
        verbose_name='ادمین'
    )
    
    action = models.CharField(max_length=50, choices=ACTION_TYPES, verbose_name='نوع عملیات')
    model = models.CharField(max_length=100, verbose_name='مدل', blank=True)
    object_id = models.CharField(max_length=100, verbose_name='شناسه شیء', blank=True)
    
    # داده‌های تغییر یافته
    old_data = models.JSONField(default=dict, blank=True, verbose_name='داده قبلی')
    new_data = models.JSONField(default=dict, blank=True, verbose_name='داده جدید')
    changes = models.JSONField(default=dict, blank=True, verbose_name='تغییرات')
    
    # اطلاعات درخواست
    ip_address = models.GenericIPAddressField(verbose_name='آی‌پی', null=True, blank=True)
    user_agent = models.TextField(verbose_name='User Agent', blank=True)
    path = models.CharField(max_length=500, verbose_name='مسیر', blank=True)
    method = models.CharField(max_length=10, verbose_name='متد', blank=True)
    
    # توضیحات
    description = models.TextField(verbose_name='توضیحات', blank=True)
    
    # اطلاعات زمانی
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='زمان')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    
    class Meta:
        verbose_name = 'لاگ ادمین'
        verbose_name_plural = 'لاگ‌های ادمین'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['admin', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
            models.Index(fields=['model', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
        permissions = [
            ('view_admin_log', 'مشاهده لاگ ادمین'),
            ('export_admin_log', 'اکسپورت لاگ ادمین'),
            ('clear_old_logs', 'پاک کردن لاگ‌های قدیمی'),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.admin} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def get_changes_summary(self):
        """خلاصه تغییرات"""
        if self.changes:
            changes_list = []
            for field, values in self.changes.items():
                if isinstance(values, dict) and 'old' in values and 'new' in values:
                    changes_list.append(f"{field}: {values['old']} → {values['new']}")
            return ", ".join(changes_list[:3]) + ("..." if len(changes_list) > 3 else "")
        return ""
    
    def get_admin_display(self):
        """نمایش ادمین"""
        if self.admin:
            return f"{self.admin.get_full_name() or self.admin.username} ({self.admin.email})"
        return "سیستم"
    
    @classmethod
    def log_action(cls, admin, action, model=None, object_id=None, 
                   old_data=None, new_data=None, changes=None,
                   request=None, description=""):
        """
        ثبت لاگ به صورت برنامه‌نویسی
        """
        log_data = {
            'admin': admin,
            'action': action,
            'model': model,
            'object_id': str(object_id) if object_id else '',
            'old_data': old_data or {},
            'new_data': new_data or {},
            'changes': changes or {},
            'description': description,
        }
        
        if request:
            log_data.update({
                'ip_address': cls.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'path': request.path[:500],
                'method': request.method,
            })
        
        return cls.objects.create(**log_data)
    
    @staticmethod
    def get_client_ip(request):
        """دریافت IP کلاینت"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class ShopActivityLog(models.Model):
    """
    لاگ فعالیت‌های هر فروشگاه
    """
    ACTION_CATEGORIES = [
        ('PLAN', 'اشتراک'),
        ('PRODUCT', 'محصول'),
        ('ORDER', 'سفارش'),
        ('CUSTOMER', 'مشتری'),
        ('SETTINGS', 'تنظیمات'),
        ('USER', 'کاربر'),
        ('PAYMENT', 'پرداخت'),
        ('SYSTEM', 'سیستم'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shop = models.ForeignKey(
        'shops.Shop',
        on_delete=models.CASCADE,
        related_name='activity_logs',
        verbose_name='فروشگاه'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='shop_activities',
        verbose_name='کاربر'
    )
    
    category = models.CharField(max_length=20, choices=ACTION_CATEGORIES, verbose_name='دسته‌بندی')
    action = models.CharField(max_length=100, verbose_name='عملیات')
    
    # اطلاعات عملیات
    details = models.JSONField(default=dict, blank=True, verbose_name='جزئیات')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='متادیتا')
    
    # اطلاعات فنی
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='آی‌پی')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    session_key = models.CharField(max_length=100, blank=True, verbose_name='کلید سشن')
    
    # زمان
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='زمان')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    
    class Meta:
        verbose_name = 'لاگ فعالیت فروشگاه'
        verbose_name_plural = 'لاگ‌های فعالیت فروشگاه'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['shop', '-timestamp']),
            models.Index(fields=['category', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.shop.shop_name} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def log_activity(cls, shop, action, category='SYSTEM', user=None, 
                     details=None, request=None, **kwargs):
        """
        ثبت فعالیت فروشگاه
        """
        log_data = {
            'shop': shop,
            'action': action,
            'category': category,
            'user': user,
            'details': details or {},
            'metadata': kwargs,
        }
        
        if request:
            log_data.update({
                'ip_address': AdminLog.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500],
                'session_key': request.session.session_key if hasattr(request, 'session') else '',
            })
        
        return cls.objects.create(**log_data)


class SystemLog(models.Model):
    """
    لاگ سیستم‌های پلتفرم
    """
    LOG_LEVELS = [
        ('DEBUG', 'دیباگ'),
        ('INFO', 'اطلاعات'),
        ('WARNING', 'هشدار'),
        ('ERROR', 'خطا'),
        ('CRITICAL', 'بحرانی'),
    ]
    
    COMPONENTS = [
        ('AUTH', 'احراز هویت'),
        ('SHOP', 'فروشگاه'),
        ('PAYMENT', 'پرداخت'),
        ('EMAIL', 'ایمیل'),
        ('API', 'API'),
        ('DATABASE', 'دیتابیس'),
        ('TASK', 'تسک'),
        ('CACHE', 'کش'),
        ('SECURITY', 'امنیت'),
        ('MONITORING', 'مانیتورینگ'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    level = models.CharField(max_length=10, choices=LOG_LEVELS, verbose_name='سطح')
    component = models.CharField(max_length=20, choices=COMPONENTS, verbose_name='کامپوننت')
    
    # پیام لاگ
    message = models.TextField(verbose_name='پیام')
    traceback = models.TextField(blank=True, verbose_name='تریس‌بک')
    
    # اطلاعات اضافی
    data = models.JSONField(default=dict, blank=True, verbose_name='داده‌ها')
    
    # اطلاعات محیطی
    hostname = models.CharField(max_length=255, blank=True, verbose_name='نام هاست')
    process_id = models.IntegerField(null=True, blank=True, verbose_name='شناسه پروسه')
    thread_id = models.IntegerField(null=True, blank=True, verbose_name='شناسه ترد')
    
    # زمان
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='زمان')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    
    class Meta:
        verbose_name = 'لاگ سیستم'
        verbose_name_plural = 'لاگ‌های سیستم'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['level', '-timestamp']),
            models.Index(fields=['component', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"[{self.level}] {self.component} - {self.message[:100]}"
    
    @classmethod
    def debug(cls, message, component='SYSTEM', **kwargs):
        """ثبت لاگ دیباگ"""
        return cls._log('DEBUG', message, component, **kwargs)
    
    @classmethod
    def info(cls, message, component='SYSTEM', **kwargs):
        """ثبت لاگ اطلاعات"""
        return cls._log('INFO', message, component, **kwargs)
    
    @classmethod
    def warning(cls, message, component='SYSTEM', **kwargs):
        """ثبت لاگ هشدار"""
        return cls._log('WARNING', message, component, **kwargs)
    
    @classmethod
    def error(cls, message, component='SYSTEM', traceback='', **kwargs):
        """ثبت لاگ خطا"""
        return cls._log('ERROR', message, component, traceback=traceback, **kwargs)
    
    @classmethod
    def critical(cls, message, component='SYSTEM', traceback='', **kwargs):
        """ثبت لاگ بحرانی"""
        log = cls._log('CRITICAL', message, component, traceback=traceback, **kwargs)
        
        # اطلاع به ادمین‌ها
        from django.core.mail import mail_admins
        try:
            mail_admins(
                subject=f'🚨 خطای بحرانی: {component}',
                message=f'{message}\n\n{traceback}',
                fail_silently=True
            )
        except Exception:
            pass
        
        return log
    
    @classmethod
    def _log(cls, level, message, component, **kwargs):
        """ثبت لاگ پایه"""
        import socket
        import os
        
        log_data = {
            'level': level,
            'component': component,
            'message': str(message)[:1000],
            'data': kwargs.get('data', {}),
        }
        
        if 'traceback' in kwargs:
            log_data['traceback'] = str(kwargs['traceback'])[:2000]
        
        # اطلاعات سیستم
        try:
            log_data['hostname'] = socket.gethostname()
            log_data['process_id'] = os.getpid()
        except:
            pass
        
        return cls.objects.create(**log_data)


class APILog(models.Model):
    """
    لاگ درخواست‌های API
    """
    REQUEST_METHODS = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # اطلاعات درخواست
    method = models.CharField(max_length=10, choices=REQUEST_METHODS, verbose_name='متد')
    path = models.CharField(max_length=500, verbose_name='مسیر')
    query_params = models.JSONField(default=dict, blank=True, verbose_name='پارامترهای کوئری')
    headers = models.JSONField(default=dict, blank=True, verbose_name='هدرها')
    
    # اطلاعات کاربر
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_logs',
        verbose_name='کاربر'
    )
    
    # اطلاعات پاسخ
    status_code = models.IntegerField(verbose_name='کد وضعیت')
    response_time = models.FloatField(verbose_name='زمان پاسخ (ثانیه)')
    response_size = models.IntegerField(default=0, verbose_name='حجم پاسخ (بایت)')
    
    # اطلاعات خطا
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    error_traceback = models.TextField(blank=True, verbose_name='تریس‌بک خطا')
    
    # اطلاعات کلاینت
    ip_address = models.GenericIPAddressField(verbose_name='آی‌پی')
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    referer = models.URLField(blank=True, verbose_name='مرجع')
    
    # زمان
    timestamp = models.DateTimeField(default=timezone.now, verbose_name='زمان')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')
    
    class Meta:
        verbose_name = 'لاگ API'
        verbose_name_plural = 'لاگ‌های API'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['method', '-timestamp']),
            models.Index(fields=['status_code', '-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['timestamp']),
        ]
    
    def __str__(self):
        return f"{self.method} {self.path} - {self.status_code} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    def is_success(self):
        """آیا درخواست موفق بوده؟"""
        return 200 <= self.status_code < 400
    
    def is_error(self):
        """آیا درخواست خطا داشته؟"""
        return self.status_code >= 400
    
    @classmethod
    def log_request(cls, request, response, response_time, user=None):
        """
        ثبت لاگ درخواست API
        """
        import json
        
        try:
            # استخراج داده‌های درخواست
            request_data = {}
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    request_data = json.loads(request.body.decode('utf-8'))
                except:
                    request_data = {'raw_body': str(request.body)[:1000]}
            
            # استخراج هدرها
            headers = {}
            for key, value in request.headers.items():
                if key.lower() not in ['authorization', 'cookie', 'set-cookie']:
                    headers[key] = value
            
            # ایجاد لاگ
            log = cls.objects.create(
                method=request.method,
                path=request.path,
                query_params=dict(request.GET),
                headers=headers,
                user=user,
                status_code=response.status_code,
                response_time=response_time,
                response_size=len(response.content) if hasattr(response, 'content') else 0,
                ip_address=AdminLog.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                referer=request.META.get('HTTP_REFERER', '')[:500],
            )
            
            # اگر خطا وجود دارد
            if response.status_code >= 400:
                try:
                    response_data = json.loads(response.content.decode('utf-8'))
                    if 'error' in response_data:
                        log.error_message = str(response_data.get('error'))[:1000]
                        log.save()
                except:
                    pass
            
            return log
            
        except Exception as e:
            SystemLog.error(f"Failed to log API request: {str(e)}", component='API')
            return None


class LogCleanupJob(models.Model):
    """
    مدیریت پاک‌سازی لاگ‌های قدیمی
    """
    JOB_TYPES = [
        ('ADMIN_LOG', 'لاگ ادمین'),
        ('SHOP_ACTIVITY', 'فعالیت فروشگاه'),
        ('SYSTEM_LOG', 'لاگ سیستم'),
        ('API_LOG', 'لاگ API'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    job_type = models.CharField(max_length=20, choices=JOB_TYPES, verbose_name='نوع کار')
    
    # تنظیمات
    retention_days = models.IntegerField(default=90, verbose_name='روزهای نگهداری')
    batch_size = models.IntegerField(default=1000, verbose_name='اندازه بچ')
    
    # نتایج
    deleted_count = models.IntegerField(default=0, verbose_name='تعداد حذف شده')
    error_count = models.IntegerField(default=0, verbose_name='تعداد خطا')
    
    # زمان
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='زمان شروع')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='زمان پایان')
    duration = models.FloatField(null=True, blank=True, verbose_name='مدت زمان (ثانیه)')
    
    # وضعیت
    is_success = models.BooleanField(default=False, verbose_name='موفقیت‌آمیز')
    error_message = models.TextField(blank=True, verbose_name='پیام خطا')
    
    class Meta:
        verbose_name = 'کار پاک‌سازی لاگ'
        verbose_name_plural = 'کارهای پاک‌سازی لاگ'
        ordering = ['-started_at']
    
    def __str__(self):
        status = "✅ موفق" if self.is_success else "❌ ناموفق"
        return f"{self.get_job_type_display()} - {status} - {self.started_at.strftime('%Y-%m-%d')}"
    
    def run_cleanup(self):
        """اجرای پاک‌سازی"""
        import time
        from django.utils import timezone
        from django.db import connection
        
        start_time = time.time()
        
        try:
            cutoff_date = timezone.now() - timezone.timedelta(days=self.retention_days)
            
            if self.job_type == 'ADMIN_LOG':
                from .models import AdminLog
                deleted, _ = AdminLog.objects.filter(
                    timestamp__lt=cutoff_date
                ).delete()
                
            elif self.job_type == 'SHOP_ACTIVITY':
                from .models import ShopActivityLog
                deleted, _ = ShopActivityLog.objects.filter(
                    timestamp__lt=cutoff_date
                ).delete()
                
            elif self.job_type == 'SYSTEM_LOG':
                from .models import SystemLog
                deleted, _ = SystemLog.objects.filter(
                    timestamp__lt=cutoff_date
                ).delete()
                
            elif self.job_type == 'API_LOG':
                from .models import APILog
                deleted, _ = APILog.objects.filter(
                    timestamp__lt=cutoff_date
                ).delete()
            
            else:
                deleted = 0
            
            # بهینه‌سازی جدول
            try:
                with connection.cursor() as cursor:
                    cursor.execute(f"VACUUM logs_{self.job_type.lower()}")
            except:
                pass
            
            self.deleted_count = deleted
            self.is_success = True
            
        except Exception as e:
            self.error_count += 1
            self.error_message = str(e)[:1000]
            self.is_success = False
        
        finally:
            end_time = time.time()
            self.finished_at = timezone.now()
            self.duration = round(end_time - start_time, 2)
            self.save()
    
    @classmethod
    def run_all_cleanups(cls):
        """اجرای همه پاک‌سازی‌ها"""
        results = []
        
        for job_type, _ in cls.JOB_TYPES:
            job = cls.objects.create(
                job_type=job_type,
                retention_days=90,
                batch_size=1000
            )
            job.run_cleanup()
            results.append({
                'type': job_type,
                'success': job.is_success,
                'deleted': job.deleted_count,
                'duration': job.duration
            })
        
        return results