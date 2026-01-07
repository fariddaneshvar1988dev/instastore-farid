from django.contrib import admin

# Register your models here.
# logs/admin.py
from django.contrib import admin
from .models import AdminLog, ShopActivityLog, SystemLog, APILog, LogCleanupJob

@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'model', 'timestamp', 'ip_address')
    list_filter = ('action', 'model', 'timestamp')
    search_fields = ('admin__username', 'description', 'ip_address')
    readonly_fields = ('timestamp', 'created_at')
    date_hierarchy = 'timestamp'

@admin.register(ShopActivityLog)
class ShopActivityLogAdmin(admin.ModelAdmin):
    list_display = ('shop', 'category', 'action', 'user', 'timestamp')
    list_filter = ('category', 'action', 'timestamp')
    search_fields = ('shop__shop_name', 'action', 'details')
    readonly_fields = ('timestamp', 'created_at')

@admin.register(SystemLog)
class SystemLogAdmin(admin.ModelAdmin):
    list_display = ('level', 'component', 'message_short', 'timestamp')
    list_filter = ('level', 'component', 'timestamp')
    search_fields = ('message', 'component')
    readonly_fields = ('timestamp', 'created_at')
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'پیام'

@admin.register(APILog)
class APILogAdmin(admin.ModelAdmin):
    list_display = ('method', 'path', 'status_code', 'user', 'response_time', 'timestamp')
    list_filter = ('method', 'status_code', 'timestamp')
    search_fields = ('path', 'ip_address')
    readonly_fields = ('timestamp', 'created_at')

@admin.register(LogCleanupJob)
class LogCleanupJobAdmin(admin.ModelAdmin):
    list_display = ('job_type', 'retention_days', 'deleted_count', 'is_success', 'started_at')
    list_filter = ('job_type', 'is_success', 'started_at')
    readonly_fields = ('started_at', 'finished_at', 'duration', 'deleted_count', 'error_count')