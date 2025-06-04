from datetime import datetime
import logging
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
from django.db import transaction, DatabaseError
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from .models import ChildDevice, AppUsageLog, ScreenTimeRule, BlockedApp
from .serializers import DeviceSerializer, AppUsageSerializer, UserSerializer

logger = logging.getLogger(__name__)

from collections import defaultdict
from django.db.models import Sum
from django.db.models.functions import TruncDate

class UsageDataAPI(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, device_id):
        try:
            device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
            
            apps = {}
            logs = AppUsageLog.objects.filter(device=device)
            
            for log in logs:
                apps[log.app_name] = apps.get(log.app_name, 0) + log.duration

            # Now compute screen time per day
            daily_logs = logs.annotate(date=TruncDate('start_time')) \
                             .values('date') \
                             .annotate(total_duration=Sum('duration')) \
                             .order_by('date')
            
            daily_labels = [str(entry['date']) for entry in daily_logs]
            daily_data = [round(entry['total_duration'] / 3600, 2) for entry in daily_logs]

            return Response({
                'labels': list(apps.keys()),         # for pie chart
                'data': [round(v/3600, 2) for v in apps.values()],  # for pie chart
                'daily_labels': daily_labels,        # for line chart
                'daily_data': daily_data,            # for line chart
                'device': device.device_id
            })
            
        except ChildDevice.DoesNotExist:
            return Response(
                {"error": "Device not found or access denied"},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def register_device(request):
    try:
        device_id = request.data.get('device_id')
        nickname = request.data.get('nickname', '')
        
        # Check if this parent already has this device
        if ChildDevice.objects.filter(parent=request.user, device_id=device_id).exists():
            return Response({"status": "device already registered to this parent"})
            
        ChildDevice.objects.create(
            parent=request.user,
            device_id=device_id,
            nickname=nickname
        )
        return Response({"status": "success"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)
    

@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def sync_usage(request):
    try:
        # Log the Authorization header
        auth_header = request.headers.get('Authorization', '')
        logger.debug(f"Authorization header: {auth_header}")
        print(f"Authorization header: {auth_header}")

        if auth_header.startswith("Bearer "):
            token_str = auth_header.split(' ')[1]
            try:
                token = AccessToken(token_str)
                logger.debug(f"Token payload: {token.payload}")
                print(f"Token payload: {token.payload}")
            except TokenError as e:
                logger.error(f"Invalid token format or error: {str(e)}")
                print(f"Invalid token format or error: {str(e)}")

        device_id = request.data.get('device_id')
        
        # Use database transaction for consistency
        with transaction.atomic():
            try:
                device = ChildDevice.objects.select_for_update().get(device_id=device_id, parent=request.user)
            except ChildDevice.DoesNotExist:
                return Response({"error": "Device not found"}, status=404)

            usage_data = request.data.get('usage_data', [])
            if not isinstance(usage_data, list):
                return Response({"error": "usage_data should be a list"}, status=400)

            valid_entries = 0
            skipped_entries = 0
            error_entries = []

            for i, entry in enumerate(usage_data):
                try:
                    # Validate required fields
                    if not entry.get('app_name'):
                        error_entries.append(f"Entry {i}: Missing app_name")
                        skipped_entries += 1
                        continue
                        
                    if not entry.get('start_time') or not entry.get('end_time'):
                        error_entries.append(f"Entry {i}: Missing start_time or end_time")
                        skipped_entries += 1
                        continue

                    # Parse timestamps with better error handling
                    try:
                        start_time_str = entry.get('start_time')
                        end_time_str = entry.get('end_time')
                        
                        # Handle different timestamp formats
                        if start_time_str.endswith('Z'):
                            start_time_str = start_time_str.replace('Z', '+00:00')
                        if end_time_str.endswith('Z'):
                            end_time_str = end_time_str.replace('Z', '+00:00')
                        
                        start_time = datetime.fromisoformat(start_time_str)
                        end_time = datetime.fromisoformat(end_time_str)
                        
                    except ValueError as e:
                        error_entries.append(f"Entry {i}: Invalid timestamp format - {str(e)}")
                        skipped_entries += 1
                        continue
                    
                    # Validate time range with detailed logging
                    if end_time <= start_time:
                        logger.warning(f"Entry {i}: Invalid time range - end_time ({end_time}) <= start_time ({start_time}) for app '{entry.get('app_name')}'. Skipping.")
                        error_entries.append(f"Entry {i}: end_time must be after start_time")
                        skipped_entries += 1
                        continue
                    
                    # Calculate and validate duration
                    duration_seconds = (end_time - start_time).total_seconds()
                    if duration_seconds <= 0:
                        logger.warning(f"Entry {i}: Invalid duration ({duration_seconds}s) for app '{entry.get('app_name')}'. Skipping.")
                        error_entries.append(f"Entry {i}: Invalid duration ({duration_seconds}s)")
                        skipped_entries += 1
                        continue
                    
                    # Additional validation: check for reasonable duration (not more than 24 hours)
                    if duration_seconds > 86400:  # 24 hours in seconds
                        logger.warning(f"Entry {i}: Suspiciously long duration ({duration_seconds}s) for app '{entry.get('app_name')}'. Skipping.")
                        error_entries.append(f"Entry {i}: Duration too long ({duration_seconds}s)")
                        skipped_entries += 1
                        continue
                    
                    # Create the AppUsageLog instance
                    app_log = AppUsageLog(
                        device=device,
                        app_name=entry.get('app_name'),
                        start_time=start_time,
                        end_time=end_time
                    )
                    app_log.save()
                    valid_entries += 1
                    
                except Exception as e:
                    logger.error(f"Entry {i}: Unexpected error - {str(e)}")
                    error_entries.append(f"Entry {i}: {str(e)}")
                    skipped_entries += 1

            device.last_sync = datetime.now(timezone.utc)
            device.save()

            response_data = {
                "status": "synced",
                "total_entries": len(usage_data),
                "valid_entries": valid_entries,
                "skipped_entries": skipped_entries
            }
            
            if error_entries:
                response_data["errors"] = error_entries[:10]  # Limit to first 10 errors
                if len(error_entries) > 10:
                    response_data["additional_errors"] = len(error_entries) - 10
            
            logger.info(f"Sync completed for device {device_id}: {valid_entries} valid, {skipped_entries} skipped out of {len(usage_data)} total entries")
            
            return Response(response_data)
            
    except DatabaseError as e:
        logger.error(f"Database error during sync for device {device_id}: {str(e)}")
        return Response({"error": "Database error occurred"}, status=500)
    except Exception as e:
        logger.error(f"Sync usage error: {e}")
        return Response({"error": str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_usage_report(request, device_id):
    logs = AppUsageLog.objects.filter(device__device_id=device_id)
    serializer = AppUsageSerializer(logs, many=True)
    return Response(serializer.data)


def parse_time(value):
    try:
        # Try with seconds first
        return datetime.strptime(value, '%H:%M:%S').time()
    except ValueError:
        # If failed, try without seconds
        return datetime.strptime(value, '%H:%M').time()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_screen_time(request):
    logger.info(f"API request received to set screen time. Request data: {request.data}")

    try:
        device = ChildDevice.objects.get(
            device_id=request.data.get('device_id'),
            parent=request.user
        )
        logger.debug(f"Found device: {device}")
        
        # Parse daily limit
        daily_limit = request.data.get('daily_limit_minutes')
        try:
            daily_limit = int(daily_limit) if daily_limit is not None else 120
        except (ValueError, TypeError):
            logger.warning(f"Invalid daily_limit_minutes value: {daily_limit}, using default 120")
            daily_limit = 120

        # Parse bedtime start
        bedtime_start_str = request.data.get('bedtime_start')
        bedtime_end_str = request.data.get('bedtime_end')
        
        bedtime_start = None
        bedtime_end = None
        
        if bedtime_start_str:
            try:
                if len(bedtime_start_str.split(":")) == 2:
                    bedtime_start = datetime.strptime(bedtime_start_str, '%H:%M').time()
                else:
                    bedtime_start = datetime.strptime(bedtime_start_str, '%H:%M:%S').time()
                logger.debug(f"Parsed bedtime_start: {bedtime_start}")
            except ValueError as e:
                logger.warning(f"Failed to parse bedtime_start: {bedtime_start_str} ({e})")
        
        if bedtime_end_str:
            try:
                if len(bedtime_end_str.split(":")) == 2:
                    bedtime_end = datetime.strptime(bedtime_end_str, '%H:%M').time()
                else:
                    bedtime_end = datetime.strptime(bedtime_end_str, '%H:%M:%S').time()
                logger.debug(f"Parsed bedtime_end: {bedtime_end}")
            except ValueError as e:
                logger.warning(f"Failed to parse bedtime_end: {bedtime_end_str} ({e})")

        # Update or create the rule
        # force assigning fields manually
        rule, created = ScreenTimeRule.objects.get_or_create(device=device)

        rule.daily_limit_minutes = daily_limit

        if bedtime_start is not None:
            rule.bedtime_start = bedtime_start
        if bedtime_end is not None:
            rule.bedtime_end = bedtime_end

        rule.save()

        
        logger.info(f"Screen time rule {'created' if created else 'updated'} successfully: {rule}")
        
        return Response({
            "status": "updated",
            "daily_limit_minutes": rule.daily_limit_minutes,
            "bedtime_start": rule.bedtime_start.strftime('%H:%M:%S') if rule.bedtime_start else None,
            "bedtime_end": rule.bedtime_end.strftime('%H:%M:%S') if rule.bedtime_end else None
        })

    except ChildDevice.DoesNotExist:
        logger.error(f"ChildDevice with id {request.data.get('device_id')} does not exist for user {request.user}")
        return Response({"error": "Device not found"}, status=404)
    except Exception as e:
        logger.exception(f"Error occurred while setting screen time: {str(e)}")
        return Response({"error": str(e)}, status=400)

    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def block_app(request):
    try:
        device_id = request.data.get('device_id')
        app_name = request.data.get('app_name')
        package_name = request.data.get('package_name', '')
        
        # Validate required fields
        if not device_id or not app_name:
            return Response(
                {"error": "device_id and app_name are required"}, 
                status=400
            )
        
        # Get device and verify ownership
        device = ChildDevice.objects.get(
            device_id=device_id,
            parent=request.user
        )
        
        # Check if app is already blocked
        existing_block = BlockedApp.objects.filter(
            device=device,
            app_name=app_name,
            is_active=True
        ).first()
        
        if existing_block:
            logger.info(f"App {app_name} is already blocked for device {device_id}")
            return Response({
                "status": "already_blocked",
                "message": f"{app_name} is already blocked",
                "app_id": existing_block.id
            })
        
        # Create new blocked app entry
        blocked_app = BlockedApp.objects.create(
            device=device,
            app_name=app_name,
            package_name=package_name,
            blocked_by=request.user,
            notes=f"Blocked via API at {timezone.now()}"
        )
        
        logger.info(f"Created blocked app: {app_name} (Package: {package_name}) for device {device_id}")
        
        # Trigger immediate sync to Android device
        from parent_ui.tasks import send_blocked_app_notification, trigger_immediate_sync
        
        # Send notification synchronously celery task
        send_blocked_app_notification(device_id, app_name, package_name)
        
        # Trigger immediate sync
        trigger_immediate_sync(device_id)
        
        # Mark the app as synced (will be updated when device actually syncs)
        blocked_app.last_synced = timezone.now()
        blocked_app.save(update_fields=['last_synced'])
        
        logger.info(f"Successfully blocked app {app_name} and triggered device sync for {device_id}")
        
        return Response({
            "status": "app_blocked",
            "message": f"{app_name} has been blocked successfully",
            "app_id": blocked_app.id,
            "package_name": package_name,
            "sync_triggered": True,
            "blocked_at": blocked_app.blocked_at.isoformat()
        })
        
    except ChildDevice.DoesNotExist:
        logger.error(f"Device {request.data.get('device_id')} not found for user {request.user}")
        return Response(
            {"error": "Device not found or access denied"}, 
            status=404
        )
    except Exception as e:
        logger.exception(f"Error blocking app: {str(e)}")
        return Response({"error": str(e)}, status=400)
    

class CustomTokenObtainPairView(TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Get the user from the validated token
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.user
            return Response({
                'access': response.data['access'],
                'refresh': response.data['refresh'],
                'user': UserSerializer(user).data
            })
        return response


@api_view(['POST'])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        if user:
            return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_screen_time_rules(request, device_id):
    try:
        device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
        rule = ScreenTimeRule.objects.get(device=device)
        return Response({
            'daily_limit_minutes': rule.daily_limit_minutes,
            'bedtime_start': rule.bedtime_start,
            'bedtime_end': rule.bedtime_end
        })
    except ScreenTimeRule.DoesNotExist:
        return Response({
            'daily_limit_minutes': 120,  # Default value
            'bedtime_start': None,
            'bedtime_end': None
        })
    except ChildDevice.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_blocked_apps(request, device_id):
    """
    API endpoint for Android app to get list of blocked apps for a device.
    Returns package names so the Android app can block them correctly.
    """
    # Log request information for debugging
    logger.info(f"get_blocked_apps called for device_id: {device_id}")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Authenticated user: {request.user}")
    
    # Print to console for immediate feedback
    print(f"get_blocked_apps: Request received for device_id={device_id}")
    print(f"get_blocked_apps: Authorization header: {request.headers.get('Authorization', 'None')}")
    
    try:
        # Get device for the authenticated user
        device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
        
        # Get all active blocked apps for this device
        blocked_apps = BlockedApp.objects.filter(device=device, is_active=True)
        
        # Extract package names - prioritize package_name over app_name
        package_names = []
        for app in blocked_apps:
            if app.package_name and app.package_name.strip():
                # Use package name if available (this is what Android needs)
                package_names.append(app.package_name.strip())
            else:
                # Fallback to app name if no package name available
                package_names.append(app.app_name)
        
        logger.info(f"Returning blocked apps for device {device_id}: {package_names}")
        
        return Response({
            'blocked_apps': package_names,
            'device_id': device_id,
            'total_count': len(package_names)
        })
        
    except ChildDevice.DoesNotExist:
        logger.error(f"Device {device_id} not found for user {request.user}")
        return Response({"error": "Device not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting blocked apps for device {device_id}: {str(e)}")
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def force_sync_blocked_apps(request, device_id):
    """
    Force immediate sync of blocked apps for a specific device.
    This endpoint can be called when the Android app receives a push notification
    or wants to immediately check for updates.
    """
    try:
        # Get device for the authenticated user (parent)
        device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
        
        # Get all active blocked apps for this device
        blocked_apps = BlockedApp.objects.filter(device=device, is_active=True)
        
        # Extract package names
        package_names = []
        for app in blocked_apps:
            if app.package_name and app.package_name.strip():
                package_names.append(app.package_name.strip())
            else:
                package_names.append(app.app_name)
        
        # Update last_synced timestamp for all blocked apps
        blocked_apps.update(last_synced=timezone.now())
        
        logger.info(f"Force sync: Returning {len(package_names)} blocked apps for device {device_id}")
        
        # Log to the console for immediate feedback
        print(f"Force sync: Device {device_id} - Blocked apps: {package_names}")

        return Response({
            'status': 'success',
            'blocked_apps': package_names,
            'device_id': device_id,
            'total_count': len(package_names),
            'synced_at': timezone.now().isoformat()
        })
        
    except ChildDevice.DoesNotExist:
        logger.error(f"Device {device_id} not found for user {request.user}")
        return Response({"error": "Device not found"}, status=404)
    except Exception as e:
        logger.error(f"Error in force sync for device {device_id}: {str(e)}")
        return Response({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_immediate_sync(request, device_id):
    """
    Trigger immediate sync notification for a specific device.
    This can be called from the web interface when an app is blocked/unblocked.
    """
    try:
        # Verify device belongs to the authenticated user
        device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
        
        action = request.data.get('action', 'sync')  # sync, block, unblock
        app_name = request.data.get('app_name', '')
        
        logger.info(f"Triggering immediate sync for device {device_id}, action: {action}, app: {app_name}")
        
        # For now, just log the trigger since we're using polling
        # In a real FCM implementation, you would send a push notification here
        
        return Response({
            'status': 'success',
            'message': f'Sync trigger sent for device {device_id}',
            'action': action,
            'app_name': app_name
        })
        
    except ChildDevice.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)
    except Exception as e:
        logger.error(f"Error triggering sync for device {device_id}: {str(e)}")
        return Response({"error": str(e)}, status=500)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def device_status(request, device_id):
    """
    Handle device status requests - used as keep-alive and status check.
    GET: Returns device status information
    POST: Updates device status (last seen, etc.)
    """
    try:
        # Get device for the authenticated user (parent)
        device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
        
        if request.method == 'GET':
            # Return device status information
            return Response({
                'status': 'success',
                'device_id': device_id,
                'device_name': device.device_name,
                'last_seen': device.last_seen.isoformat() if device.last_seen else None,
                'is_active': True,
                'timestamp': timezone.now().isoformat()
            })
        
        elif request.method == 'POST':
            # Update device last seen timestamp
            device.last_seen = timezone.now()
            device.save()
            
            logger.info(f"Updated device status for {device_id}")
            
            return Response({
                'status': 'success',
                'message': 'Device status updated',
                'device_id': device_id,
                'timestamp': timezone.now().isoformat()
            })
        
    except ChildDevice.DoesNotExist:
        logger.warning(f"Device not found for status check: {device_id}")
        return Response({"error": "Device not found"}, status=404)
    except Exception as e:
        logger.error(f"Error handling device status for {device_id}: {str(e)}")
        return Response({"error": str(e)}, status=500)