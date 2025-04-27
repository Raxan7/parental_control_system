import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')

app = Celery('parental_control_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()