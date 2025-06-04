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
