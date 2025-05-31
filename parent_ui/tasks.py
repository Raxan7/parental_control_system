import requests
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_blocked_app_notification(device_id, app_name, package_name=None):
    """
    Send a push notification to the device about a newly blocked app
    """
    try:
        # In a real implementation, you would send this to your push notification service
        # For now, we'll just log it since we're handling the sync via API polling
        logger.info(f"App blocked notification - Device: {device_id}, App: {app_name}, Package: {package_name}")
        
        # Example implementation with Firebase Cloud Messaging:
        # if hasattr(settings, 'FCM_SERVER_KEY'):
        #     from pyfcm import FCMNotification
        #     push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
        #     push_service.notify_single_device(
        #         registration_id=device_id,
        #         message_title="App Blocked",
        #         message_body=f"{app_name} has been blocked"
        #     )
    except Exception as e:
        logger.error(f"Failed to send blocked app notification: {str(e)}")

def send_screen_time_update(device_id, daily_limit_minutes):
    """
    Send a push notification to the device about screen time limit changes
    """
    try:
        logger.info(f"Screen time updated - Device: {device_id}, New limit: {daily_limit_minutes} minutes")
        
        # Example FCM implementation:
        # if hasattr(settings, 'FCM_SERVER_KEY'):
        #     from pyfcm import FCMNotification
        #     push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
        #     push_service.notify_single_device(
        #         registration_id=device_id,
        #         message_title="Screen Time Updated",
        #         message_body=f"New daily limit: {daily_limit_minutes} minutes"
        #     )
    except Exception as e:
        logger.error(f"Failed to send screen time update: {str(e)}")

def send_unblocked_app_notification(device_id, app_name, package_name=None):
    """
    Send a push notification to the device about a newly unblocked app
    """
    try:
        logger.info(f"App unblocked notification - Device: {device_id}, App: {app_name}, Package: {package_name}")
        
        # In a real implementation, you would send this to your push notification service
        # For now, we'll just log it since we're handling the sync via API polling
        # Example implementation with Firebase Cloud Messaging:
        # if hasattr(settings, 'FCM_SERVER_KEY'):
        #     from pyfcm import FCMNotification
        #     push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
        #     push_service.notify_single_device(
        #         registration_id=device_id,
        #         message_title="App Unblocked",
        #         message_body=f"{app_name} is now available"
        #     )
    except Exception as e:
        logger.error(f"Failed to send unblocked app notification: {str(e)}")

def trigger_immediate_sync(device_id):
    """
    Trigger immediate sync for a specific device
    This function can be called when critical changes need to be synced immediately
    """
    try:
        logger.info(f"Triggering immediate sync for device: {device_id}")
        
        # In a real implementation with push notifications:
        # if hasattr(settings, 'FCM_SERVER_KEY'):
        #     from pyfcm import FCMNotification
        #     push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
        #     push_service.notify_single_device(
        #         registration_id=device_id,
        #         message_title="Sync Required",
        #         message_body="Please sync with server",
        #         data_message={"action": "immediate_sync", "timestamp": str(timezone.now())}
        #     )
        
        return f"Immediate sync triggered for device {device_id}"
    except Exception as e:
        logger.error(f"Failed to trigger immediate sync for device {device_id}: {str(e)}")
        return f"Failed to trigger sync: {str(e)}"