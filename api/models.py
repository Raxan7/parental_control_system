from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import uuid

class CustomUser(AbstractUser):
    is_parent = models.BooleanField(default=False)
    is_child = models.BooleanField(default=False)
    
    # Email verification fields
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # If this is a new user, set is_active to False until email is verified
        if self.pk is None and not self.is_email_verified:
            self.is_active = False
        super().save(*args, **kwargs)

class ChildDevice(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    device_id = models.CharField(max_length=255)  # Removed unique=True
    nickname = models.CharField(max_length=100, blank=True, null=True)
    last_sync = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('parent', 'device_id')  # Ensures a parent can't add same device twice

    def __str__(self):
        return self.nickname if self.nickname else self.device_id

class AppUsageLog(models.Model):
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE)
    app_name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    
    def clean(self):
        """Validate that end_time is after start_time"""
        from django.core.exceptions import ValidationError
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
    
    def save(self, *args, **kwargs):
        # Calculate duration and ensure it's positive
        if self.end_time and self.start_time:
            duration_seconds = (self.end_time - self.start_time).total_seconds()
            if duration_seconds <= 0:
                # If duration is not positive, set to 1 second minimum
                self.duration = 1
            else:
                self.duration = int(duration_seconds)
        else:
            self.duration = 0
            
        # Call clean method for validation
        self.clean()
        super().save(*args, **kwargs)
    
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(end_time__gt=models.F('start_time')),
                name='end_time_after_start_time'
            )
        ]

from django.db import models
from django.utils import timezone

class BlockedApp(models.Model):
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE, related_name='blocked_apps')
    app_name = models.CharField(max_length=100, help_text="User-friendly name of the application")
    package_name = models.CharField(
        max_length=200, 
        help_text="Android package name (e.g., com.example.app)",
        blank=True,
        null=True
    )
    blocked_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_apps'
    )
    notes = models.TextField(blank=True, null=True, help_text="Optional reason for blocking")

    class Meta:
        unique_together = ('device', 'package_name')
        ordering = ['-blocked_at']
        verbose_name = "Blocked Application"
        verbose_name_plural = "Blocked Applications"

    def __str__(self):
        return f"{self.app_name} (Blocked for {self.device})"

    def save(self, *args, **kwargs):
        # Ensure package_name is cleaned (remove whitespace, etc.)
        if self.package_name:
            self.package_name = self.package_name.strip()
        super().save(*args, **kwargs)

    def sync_to_device(self):
        """
        Triggers synchronization to the device
        """
        from parent_ui.tasks import send_blocked_app_notification
        send_blocked_app_notification(
            self.device.device_id,
            self.app_name,
            self.package_name
        )
        self.last_synced = timezone.now()
        self.save(update_fields=['last_synced'])


class ScreenTimeRule(models.Model):
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE)
    daily_limit_minutes = models.PositiveIntegerField(default=120)
    bedtime_start = models.TimeField(null=True, blank=True)
    bedtime_end = models.TimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Rules for {self.device.device_id}"
    

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ScreenTimeRule)
def log_screen_time_rule_save(sender, instance, created, **kwargs):
    action = "Created" if created else "Updated"
    logger.info(f"{action} ScreenTimeRule for device {instance.device.device_id}: "
                f"daily_limit_minutes={instance.daily_limit_minutes}, "
                f"bedtime_start={instance.bedtime_start}, "
                f"bedtime_end={instance.bedtime_end}")


class ScreenTime(models.Model):
    device = models.ForeignKey('ChildDevice', on_delete=models.CASCADE, related_name='screen_time_entries')
    timestamp = models.DateTimeField()  # full datetime, not just date
    minutes = models.PositiveIntegerField(default=1)  # each row represents N minutes, usually 1
    sync_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('device', 'timestamp')  # One entry per device per minute
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.device.device_id} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}: {self.minutes} minutes"

# URL Content Filtering Models
class BlockedURL(models.Model):
    """Model to store blocked URLs for content filtering"""
    BLOCK_TYPE_CHOICES = [
        ('exact', 'Exact URL'),
        ('domain', 'Entire Domain'),
        ('keyword', 'Contains Keyword'),
        ('regex', 'Regular Expression'),
    ]
    
    CATEGORY_CHOICES = [
        ('adult', 'Adult Content'),
        ('social', 'Social Media'),
        ('gaming', 'Gaming'),
        ('streaming', 'Video Streaming'),
        ('shopping', 'Shopping'),
        ('news', 'News'),
        ('education', 'Educational'),
        ('custom', 'Custom Category'),
    ]
    
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE, related_name='blocked_urls')
    url_pattern = models.TextField(help_text="URL, domain, keyword, or regex pattern to block")
    block_type = models.CharField(max_length=10, choices=BLOCK_TYPE_CHOICES, default='exact')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='custom')
    reason = models.TextField(blank=True, null=True, help_text="Reason for blocking this URL")
    blocked_at = models.DateTimeField(auto_now_add=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='blocked_urls'
    )
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('device', 'url_pattern', 'block_type')
        ordering = ['-blocked_at']
        verbose_name = "Blocked URL"
        verbose_name_plural = "Blocked URLs"
    
    def __str__(self):
        return f"{self.url_pattern} ({self.get_block_type_display()}) - {self.device}"
    
    def clean(self):
        """Validate URL patterns based on block type"""
        from django.core.exceptions import ValidationError
        import re
        
        if self.block_type == 'exact' and not self.url_pattern.startswith(('http://', 'https://')):
            self.url_pattern = 'https://' + self.url_pattern
        
        if self.block_type == 'regex':
            try:
                re.compile(self.url_pattern)
            except re.error:
                raise ValidationError("Invalid regular expression pattern")
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class URLAccessLog(models.Model):
    """Log URL access attempts for monitoring and reporting"""
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE, related_name='url_access_logs')
    url = models.URLField(max_length=2048)
    domain = models.CharField(max_length=255, db_index=True)
    access_time = models.DateTimeField()
    was_blocked = models.BooleanField(default=False)
    blocked_by_rule = models.ForeignKey(BlockedURL, on_delete=models.SET_NULL, null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-access_time']
        indexes = [
            models.Index(fields=['device', 'access_time']),
            models.Index(fields=['domain', 'access_time']),
            models.Index(fields=['was_blocked', 'access_time']),
        ]
    
    def __str__(self):
        status = "BLOCKED" if self.was_blocked else "ALLOWED"
        return f"{self.device} - {self.domain} [{status}] at {self.access_time}"
    
    def save(self, *args, **kwargs):
        # Extract domain from URL if not set
        if not self.domain and self.url:
            from urllib.parse import urlparse
            parsed = urlparse(self.url)
            self.domain = parsed.netloc.lower()
        super().save(*args, **kwargs)


class SafeBrowsingCategory(models.Model):
    """Predefined categories for safe browsing"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-shield-alt')
    color = models.CharField(max_length=20, default='#dc3545')
    is_enabled_by_default = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Safe Browsing Category"
        verbose_name_plural = "Safe Browsing Categories"


class DeviceContentFilter(models.Model):
    """Device-specific content filtering settings"""
    device = models.OneToOneField(ChildDevice, on_delete=models.CASCADE, related_name='content_filter')
    enabled = models.BooleanField(default=True)
    strict_mode = models.BooleanField(default=False, help_text="Block unknown/unclassified websites")
    allow_search_engines = models.BooleanField(default=True)
    allow_educational = models.BooleanField(default=True)
    blocked_categories = models.ManyToManyField(SafeBrowsingCategory, blank=True)
    whitelist_enabled = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Content Filter for {self.device}"


class WhitelistedURL(models.Model):
    """URLs that are always allowed, even if they match blocked patterns"""
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE, related_name='whitelisted_urls')
    url_pattern = models.TextField()
    reason = models.CharField(max_length=255, blank=True, null=True)
    added_at = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        unique_together = ('device', 'url_pattern')
    
    def __str__(self):
        return f"Whitelisted: {self.url_pattern} for {self.device}"
