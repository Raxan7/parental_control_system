from datetime import timezone, datetime
import logging
import requests
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import AnonymousUser
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

class UsageDataAPI(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, device_id):
        try:
            # Debugging: Print token information
            auth_header = request.headers.get('Authorization', '')
            print(f"Auth Header: {auth_header}")
            print(f"User: {request.user}")
            print(f"User is authenticated: {request.user.is_authenticated}")
            print(f"User is anonymous: {isinstance(request.user, AnonymousUser)}")
            print(f"Request headers: {request.headers}")
            
            if auth_header:
                try:
                    raw_token = auth_header.split(' ')[1]
                    token = AccessToken(raw_token)
                    print(f"Token payload: {token.payload}")
                except (IndexError, TokenError) as e:
                    print(f"Token parsing error: {str(e)}")

            # Verify device ownership
            device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
            
            # Process data
            apps = {}
            logs = AppUsageLog.objects.filter(device=device)
            
            for log in logs:
                apps[log.app_name] = apps.get(log.app_name, 0) + log.duration
            
            return Response({
                'labels': list(apps.keys()),
                'data': [round(v/3600, 2) for v in apps.values()],
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
        device = ChildDevice.objects.get(device_id=device_id, parent=request.user)

        usage_data = request.data.get('usage_data', [])
        if not isinstance(usage_data, list):
            return Response({"error": "usage_data should be a list"}, status=400)

        for entry in usage_data:
            try:
                start_time = datetime.fromisoformat(entry.get('start_time').replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(entry.get('end_time').replace('Z', '+00:00'))
                AppUsageLog.objects.create(
                    device=device,
                    app_name=entry.get('app_name'),
                    start_time=start_time,
                    end_time=end_time
                )
            except ValueError as e:
                logger.error(f"Date/time parsing error: {e}, entry: {entry}")
                return Response({"error": f"Invalid date/time format: {e}"}, status=400)
            except KeyError as e:
                logger.error(f"Missing key in usage_data: {e}, entry: {entry}")
                return Response({"error": f"Missing key: {e}"}, status=400)

        device.last_sync = datetime.now(timezone.utc)
        device.save()

        return Response({"status": "synced"})

    except ChildDevice.DoesNotExist:
        return Response({"error": "Device not found"}, status=404)
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
        device = ChildDevice.objects.get(
            device_id=request.data.get('device_id'),
            parent=request.user
        )
        BlockedApp.objects.create(
            device=device,
            app_name=request.data.get('app_name')
        )
        return Response({"status": "app blocked"})
    except Exception as e:
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