# parent_ui/urls.py
from django.urls import path
from . import views
from . import views_app_blocking

urlpatterns = [
    path('device/<str:device_id>/', views.manage_device, name='manage_device'),
    path('device/<str:device_id>/screen-time/', views.update_screen_time, name='update_screen_time'),

    # New app blocking interface
    path('device/<str:device_id>/app-blocking/', views_app_blocking.app_blocking_view, name='app_blocking'),
    path('device/<str:device_id>/toggle-block-app/', views_app_blocking.toggle_block_app, name='toggle_block_app'),

    path('login/', views.ParentLoginView.as_view(), name='login'),
    path('', views.ParentDashboardView.as_view(), name='parent_dashboard'),

    path('events/', views.sse_events, name='sse_events'),
    path('poll-updates/', views.poll_updates, name='poll_updates'),

    path('api/device/<str:device_id>/blocked-apps/', views.get_blocked_apps, name='get_blocked_apps'),

    path('register/', views.register, name='register'),
    path('register/success/', views.RegistrationSuccessView.as_view(), name='registration_success'),
    
    # Email verification
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification_email, name='resend_verification'),
    
    # Account settings
    path('account/settings/', views.account_settings, name='account_settings'),
]