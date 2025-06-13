from django.urls import path
from . import views

urlpatterns = [
    path('register-device/', views.register_device),
    path('sync-usage/', views.sync_usage),
    path('set-screen-time/', views.set_screen_time),
    path('report/<str:device_id>/', views.get_usage_report),
    path('block-app/', views.block_app),

    # Authentication endpoints
    path('token/', views.CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', views.TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', views.TokenVerifyView.as_view(), name='token_verify'),
    path('register/', views.register, name='register'),

    path('usage-data/<str:device_id>/', views.UsageDataAPI.as_view(), name='usage_data_api'),
    path('get-screen-time-rules/<str:device_id>/', views.get_screen_time_rules, name='get_screen_time_rules'),
    path('get_blocked_apps/<str:device_id>/', views.get_blocked_apps, name='get_blocked_apps_api'),
    path('force_sync_blocked_apps/<str:device_id>/', views.force_sync_blocked_apps, name='force_sync_blocked_apps'),
    path('trigger_immediate_sync/<str:device_id>/', views.trigger_immediate_sync, name='trigger_immediate_sync'),
]