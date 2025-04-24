from django.db import models
from api.models import ChildDevice

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