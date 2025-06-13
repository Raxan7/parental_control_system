from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, 
    ChildDevice, 
    AppUsageLog, 
    BlockedApp, 
    ScreenTimeRule, 
    ScreenTime
)

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_parent', 'is_child', 'is_staff')
    list_filter = ('is_parent', 'is_child', 'is_staff', 'is_superuser', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('is_parent', 'is_child')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('User Type', {'fields': ('is_parent', 'is_child')}),
    )

@admin.register(ChildDevice)
class ChildDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'nickname', 'parent', 'last_sync', 'created_at')
    list_filter = ('parent', 'created_at', 'last_sync')
    search_fields = ('device_id', 'nickname', 'parent__username')
    readonly_fields = ('created_at',)
    
@admin.register(AppUsageLog)
class AppUsageLogAdmin(admin.ModelAdmin):
    list_display = ('device', 'app_name', 'start_time', 'end_time', 'duration')
    list_filter = ('device', 'start_time', 'app_name')
    search_fields = ('app_name', 'device__device_id', 'device__nickname')
    readonly_fields = ('duration',)
    date_hierarchy = 'start_time'

@admin.register(BlockedApp)
class BlockedAppAdmin(admin.ModelAdmin):
    list_display = ('app_name', 'package_name', 'device', 'is_active', 'blocked_at', 'last_synced')
    list_filter = ('is_active', 'blocked_at', 'device', 'blocked_by')
    search_fields = ('app_name', 'package_name', 'device__device_id', 'device__nickname')
    readonly_fields = ('blocked_at', 'last_synced')
    fieldsets = (
        ('App Information', {
            'fields': ('app_name', 'package_name')
        }),
        ('Blocking Details', {
            'fields': ('device', 'blocked_by', 'is_active', 'notes')
        }),
        ('Timestamps', {
            'fields': ('blocked_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )

@admin.register(ScreenTimeRule)
class ScreenTimeRuleAdmin(admin.ModelAdmin):
    list_display = ('device', 'daily_limit_minutes', 'bedtime_start', 'bedtime_end', 'synced_to_device', 'last_updated')
    list_filter = ('device', 'synced_to_device', 'last_updated')
    search_fields = ('device__device_id', 'device__nickname')
    readonly_fields = ('last_updated',)

@admin.register(ScreenTime)
class ScreenTimeAdmin(admin.ModelAdmin):
    list_display = ('device', 'timestamp', 'minutes', 'sync_status', 'created_at')
    list_filter = ('device', 'sync_status', 'timestamp', 'created_at')
    search_fields = ('device__device_id', 'device__nickname')
    readonly_fields = ('created_at',)
    date_hierarchy = 'timestamp'
