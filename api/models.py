from django.db import models
from django.contrib.auth.models import AbstractUser

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

class BlockedApp(models.Model):
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE)
    app_name = models.CharField(max_length=100)
    blocked_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('device', 'app_name')


class ScreenTimeRule(models.Model):
    device = models.ForeignKey(ChildDevice, on_delete=models.CASCADE)
    daily_limit_minutes = models.PositiveIntegerField(default=120)
    bedtime_start = models.TimeField(null=True)
    bedtime_end = models.TimeField(null=True)