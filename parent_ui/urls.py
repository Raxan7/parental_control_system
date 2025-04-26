# parent_ui/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('device/<str:device_id>/', views.manage_device, name='manage_device'),
    path('device/<str:device_id>/screen-time/', views.update_screen_time, name='update_screen_time'),
    path('device/<str:device_id>/block-app/', views.block_app, name='block_app'),

    path('login/', views.ParentLoginView.as_view(), name='login'),
    path('', views.ParentDashboardView.as_view(), name='parent_dashboard'),

    path('events/', views.sse_events, name='sse_events'),
    path('poll-updates/', views.poll_updates, name='poll_updates'),

    path('device/<str:device_id>/block-app/', views.block_app, name='block_app'),
    path('api/device/<str:device_id>/blocked-apps/', views.get_blocked_apps, name='get_blocked_apps'),
]