from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class CustomUser(AbstractUser):
    is_parent = models.BooleanField(default=False)
    is_child = models.BooleanField(default=False)

class ChildDevice(models.Model):
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    device_id = models.CharField(max_length=255, unique=True)
    nickname = models.CharField(max_length=100, blank=True, null=True)  # Add this field
    last_sync = models.DateTimeField(null=True)

    def __str__(self):
        return self.nickname if self.nickname else self.device_id

class AppUsageLog(models.Model):
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE)
    app_name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    duration = models.PositiveIntegerField(help_text="Duration in seconds")
    
    def save(self, *args, **kwargs):
        self.duration = (self.end_time - self.start_time).total_seconds()
        super().save(*args, **kwargs)

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
        return f"{self.app_name} (Blocked for {self.device.device_name})"

    def save(self, *args, **kwargs):
        # Ensure package_name is cleaned (remove whitespace, etc.)
        if self.package_name:
            self.package_name = self.package_name.strip()
        super().save(*args, **kwargs)

    def sync_to_device(self):
        """
        Triggers synchronization to the device
        """
        from .tasks import send_blocked_app_notification
        send_blocked_app_notification.delay(
            self.device.device_id,
            self.app_name,
            self.package_name
        )
        self.last_synced = timezone.now()
        self.save(update_fields=['last_synced'])


class ScreenTimeRule(models.Model):
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE)
    daily_limit_minutes = models.PositiveIntegerField(default=120)
    bedtime_start = models.TimeField(null=True)
    bedtime_end = models.TimeField(null=True)