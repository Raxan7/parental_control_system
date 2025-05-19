from django.db import models
from api.models import ChildDevice, CustomUser

class ParentDashboard(models.Model):
    user = models.OneToOneField('api.CustomUser', on_delete=models.CASCADE)
    theme = models.CharField(max_length=20, default='light')
    last_viewed_device = models.ForeignKey(ChildDevice, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Dashboard for {self.user.username}"
    

# models.py
class Notification(models.Model):
    user = models.ForeignKey('api.CustomUser', on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=20, choices=[
        ('warning', 'Warning'),
        ('info', 'Information'),
        ('alert', 'Alert')
    ])


class AppCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    color_code = models.CharField(max_length=10, default='#CCCCCC')
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "App Categories"


class AppIcon(models.Model):
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('unknown', 'Unknown Risk')
    ]
    
    package_name = models.CharField(max_length=200, unique=True)
    friendly_name = models.CharField(max_length=100)
    icon = models.ImageField(upload_to='app_icons/', null=True, blank=True)
    category = models.ForeignKey(AppCategory, on_delete=models.SET_NULL, null=True, blank=True)
    risk_level = models.CharField(max_length=10, choices=RISK_LEVEL_CHOICES, default='unknown')
    risk_reasons = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return self.friendly_name or self.package_name


class CustomAppMapping(models.Model):
    """Allow parents to customize how app names are displayed"""
    parent = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    package_name = models.CharField(max_length=200)
    custom_name = models.CharField(max_length=100)
    
    class Meta:
        unique_together = ('parent', 'package_name')
        
    def __str__(self):
        return f"{self.package_name} -> {self.custom_name} (for {self.parent.username})"