from django.contrib import admin
from .models import (
    ParentDashboard,
    Notification,
    AppCategory,
    AppIcon,
    CustomAppMapping
)

@admin.register(ParentDashboard)
class ParentDashboardAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'last_viewed_device')
    list_filter = ('theme',)
    search_fields = ('user__username', 'user__email')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected notifications as unread"
    
    actions = [mark_as_read, mark_as_unread]

@admin.register(AppCategory)
class AppCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'color_code')
    search_fields = ('name', 'description')
    prepopulated_fields = {'name': ('name',)}

@admin.register(AppIcon)
class AppIconAdmin(admin.ModelAdmin):
    list_display = ('friendly_name', 'package_name', 'category', 'risk_level')
    list_filter = ('category', 'risk_level')
    search_fields = ('friendly_name', 'package_name')
    fieldsets = (
        ('App Information', {
            'fields': ('package_name', 'friendly_name', 'icon')
        }),
        ('Categorization', {
            'fields': ('category', 'risk_level', 'risk_reasons')
        }),
    )

@admin.register(CustomAppMapping)
class CustomAppMappingAdmin(admin.ModelAdmin):
    list_display = ('parent', 'package_name', 'custom_name')
    list_filter = ('parent',)
    search_fields = ('parent__username', 'package_name', 'custom_name')
    
    class Meta:
        unique_together = ('parent', 'package_name')
