from datetime import timedelta
import json
import logging
import time
import requests
import csv

from django.contrib.auth import login, update_session_auth_hash, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.core import serializers
from django.http import HttpResponseForbidden, JsonResponse, StreamingHttpResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods
from django.views.generic import TemplateView
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from api.models import BlockedApp, ChildDevice, CustomUser, ScreenTimeRule, AppUsageLog
from parental_control_system import settings
from .forms import BlockAppForm, DeviceForm, ParentRegistrationForm, ScreenTimeRuleForm, AccountSettingsForm, ChangePasswordForm
from .tasks import send_blocked_app_notification

logger = logging.getLogger(__name__)

@method_decorator(login_required, name='dispatch')
class ParentDashboardView(TemplateView):
    template_name = 'parent_ui/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        if user.is_authenticated:
            context['devices'] = ChildDevice.objects.filter(parent=user)
        else:
            context['devices'] = []
        
        context['blocked_apps'] = BlockedApp.objects.filter(device__parent=user)
        context['screen_rules'] = ScreenTimeRule.objects.filter(device__parent=user)
        
        return context


def event_stream(request):
    def event_generator():
        while True:
            # Check for new data
            time.sleep(5)
            yield f"data: {json.dumps({'update': timezone.now()})}\n\n"

    return StreamingHttpResponse(event_generator(), content_type='text/event-stream')


# ...existing code...
from django.db.models import Sum
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

@login_required
def manage_device(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    # Get timeframe from request parameters (default to 7 days)
    timeframe = request.GET.get('timeframe')
    custom_days = request.GET.get('custom_days')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # Get the last used timeframe from the session, or default to 'week'
    if not timeframe:
        timeframe = request.session.get('report_timeframe', 'week')
        custom_days = request.session.get('report_custom_days')
    
    # Store the current timeframe in the session for next visit
    request.session['report_timeframe'] = timeframe
    if custom_days:
        request.session['report_custom_days'] = custom_days
    
    # Calculate the date range based on timeframe
    end_date = timezone.now()
    if timeframe == 'day':
        start_date = end_date - timezone.timedelta(days=1)
        timeframe_description = "Last 24 Hours"
    elif timeframe == 'week':
        start_date = end_date - timezone.timedelta(days=7)
        timeframe_description = "Last 7 Days"
    elif timeframe == 'month':
        start_date = end_date - timezone.timedelta(days=30)
        timeframe_description = "Last 30 Days"
    elif timeframe == 'year':
        start_date = end_date - timezone.timedelta(days=365)
        timeframe_description = "Last 365 Days"
    elif timeframe == 'custom' and custom_days and custom_days.isdigit():
        days = int(custom_days)
        start_date = end_date - timezone.timedelta(days=days)
        timeframe_description = f"Last {days} Days"
    elif timeframe == 'date_range' and from_date and to_date:
        from datetime import datetime
        try:
            start_date = timezone.make_aware(datetime.strptime(from_date, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(to_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59))
            timeframe_description = f"{from_date} to {to_date}"
        except ValueError:
            # Invalid date format, fall back to default
            start_date = end_date - timezone.timedelta(days=7)
            timeframe = 'week'
            timeframe_description = "Last 7 Days"
    else:
        # Default to week if invalid timeframe
        start_date = end_date - timezone.timedelta(days=7)
        timeframe = 'week'
        timeframe_description = "Last 7 Days"
    
    # Get usage data for this specific device within the timeframe
    logs = AppUsageLog.objects.filter(
        device=device,
        start_time__gte=start_date,
        start_time__lte=end_date
    )
    
    # Prepare data for charts
    usage_by_app = logs.values('app_name').annotate(
        total_duration=Sum('duration')
    ).order_by('-total_duration')
    
    # Daily usage data
    daily_usage = logs.extra(
        {'date': "date(start_time)"}
    ).values('date').annotate(
        total_duration=Sum('duration')
    ).order_by('date')
    
    if request.method == 'POST':
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            return redirect('parent_dashboard')
    else:
        form = DeviceForm(instance=device)

    # Get or create screen time rule for this device
    try:
        screen_time_rule = ScreenTimeRule.objects.get(device=device)
        screen_time_form = ScreenTimeRuleForm(instance=screen_time_rule)
    except ScreenTimeRule.DoesNotExist:
        # Create a default rule if none exists
        screen_time_form = ScreenTimeRuleForm()

    # Check if download was requested (PDF or CSV)
    download_format = request.GET.get('download')
    if download_format in ['pdf', 'csv']:
        return generate_report(device, logs, download_format, timeframe_description)

    return render(request, 'parent_ui/manage_device.html', context={
        'form': form,
        'device': device,
        'screen_time_form': screen_time_form,
        'block_app_form': BlockAppForm(),
        'logs': logs,
        'usage_by_app': usage_by_app,
        'daily_usage': daily_usage,
        'timeframe': timeframe,
        'custom_days': custom_days,
        'from_date': from_date,
        'to_date': to_date,
        'timeframe_description': timeframe_description,
    })

def generate_report(device, logs, format_type, timeframe_description):
    if format_type == 'pdf':
        return generate_pdf_report(device, logs, timeframe_description)
    elif format_type == 'csv':
        return generate_csv_report(device, logs, timeframe_description)

def generate_pdf_report(device, logs, timeframe_description):
    from .templatetags.custom_filters import friendly_app_name
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # PDF content
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"Device Usage Report: {device.nickname or device.device_id}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    p.drawString(100, 760, f"Timeframe: {timeframe_description}")
    
    # Table headers
    p.drawString(100, 730, "App Name")
    p.drawString(300, 730, "Start Time")
    p.drawString(400, 730, "Duration (mins)")
    
    # Table rows
    y = 710
    for log in logs.order_by('-start_time')[:50]:  # Limit to 50 most recent logs
        friendly_name = friendly_app_name(log.app_name, device.parent)
        p.drawString(100, y, friendly_name)
        p.drawString(300, y, log.start_time.strftime('%Y-%m-%d %H:%M'))
        p.drawString(400, y, f"{round(log.duration/60, 1)}")
        y -= 20
        if y < 50:  # Prevent running off the page
            p.showPage()
            y = 750
    
    # Summary
    p.showPage()
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, f"Usage Summary ({timeframe_description})")
    
    total_usage = sum(log.duration for log in logs)
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Total screen time: {round(total_usage/3600, 2)} hours")
    p.drawString(100, 750, f"Number of app sessions: {logs.count()}")
    
    # App usage breakdown
    usage_by_app = logs.values('app_name').annotate(
        total_duration=Sum('duration')
    ).order_by('-total_duration')[:10]  # Top 10 apps
    
    p.drawString(100, 720, "Top 10 Apps by Usage:")
    y = 700
    for app in usage_by_app:
        hours = app['total_duration'] / 3600
        friendly_name = friendly_app_name(app['app_name'], device.parent)
        p.drawString(100, y, f"• {friendly_name}: {round(hours, 2)} hours")
        y -= 20
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{device.device_id}_usage_report_{timeframe_description.replace(" ", "_")}.pdf"'
    return response

def generate_csv_report(device, logs, timeframe_description):
    import csv
    from django.http import HttpResponse
    from .templatetags.custom_filters import friendly_app_name
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{device.device_id}_usage_report_{timeframe_description.replace(" ", "_")}.csv"'
    
    writer = csv.writer(response)
    
    # Header information
    writer.writerow(['Device Usage Report'])
    writer.writerow(['Device', device.nickname or device.device_id])
    writer.writerow(['Generated on', datetime.now().strftime('%Y-%m-%d %H:%M')])
    writer.writerow(['Timeframe', timeframe_description])
    writer.writerow([])  # Empty row
    
    # Summary
    total_usage = sum(log.duration for log in logs)
    writer.writerow(['Summary'])
    writer.writerow(['Total screen time (hours)', round(total_usage/3600, 2)])
    writer.writerow(['Number of app sessions', logs.count()])
    writer.writerow([])  # Empty row
    
    # App usage breakdown
    usage_by_app = logs.values('app_name').annotate(
        total_duration=Sum('duration')
    ).order_by('-total_duration')
    
    writer.writerow(['App Usage Summary'])
    writer.writerow(['App Name', 'Total Duration (hours)', 'Total Duration (minutes)'])
    for app in usage_by_app:
        hours = app['total_duration'] / 3600
        minutes = app['total_duration'] / 60
        friendly_name = friendly_app_name(app['app_name'], device.parent)
        writer.writerow([friendly_name, round(hours, 2), round(minutes, 1)])
    
    writer.writerow([])  # Empty row
    
    # Detailed usage logs
    writer.writerow(['Detailed Usage Logs'])
    writer.writerow(['App Name', 'Start Time', 'End Time', 'Duration (minutes)'])
    
    for log in logs.order_by('-start_time'):
        duration_minutes = log.duration / 60
        end_time = log.end_time.strftime('%Y-%m-%d %H:%M:%S') if log.end_time else 'N/A'
        friendly_name = friendly_app_name(log.app_name, device.parent)
        writer.writerow([
            friendly_name,
            log.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time,
            round(duration_minutes, 1)
        ])
    
    return response


import logging
import requests
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Set up logger
logger = logging.getLogger(__name__)

import json

@login_required
def update_screen_time(request, device_id):
    logger.info(f"Received request to update screen time for device {device_id} by user {request.user}")

    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    if request.method == 'POST':
        # Handle both JSON and form submissions
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                logger.debug(f"Received JSON data: {data}")
            except json.JSONDecodeError:
                return JsonResponse({'error': 'Invalid JSON'}, status=400)
        else:
            # Handle form submission
            data = request.POST.dict()
            logger.debug(f"Received form data: {data}")
        
        daily_limit_minutes = data.get('daily_limit_minutes')
        bedtime_start = data.get('bedtime_start')
        bedtime_end = data.get('bedtime_end')
        
        if not daily_limit_minutes:
            error_msg = 'Daily limit is required'
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'error': error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect('manage_device', device_id=device_id)
        
        try:
            # Validate daily limit
            daily_limit_minutes = int(daily_limit_minutes)
            if daily_limit_minutes < 1 or daily_limit_minutes > 1440:
                raise ValueError("Daily limit must be between 1 and 1440 minutes")
            
            # Parse time fields if provided
            bedtime_start_time = None
            bedtime_end_time = None
            
            if bedtime_start:
                try:
                    bedtime_start_time = datetime.strptime(bedtime_start, '%H:%M').time()
                except ValueError:
                    try:
                        bedtime_start_time = datetime.strptime(bedtime_start, '%H:%M:%S').time()
                    except ValueError:
                        logger.warning(f"Invalid bedtime start format: {bedtime_start}")
            
            if bedtime_end:
                try:
                    bedtime_end_time = datetime.strptime(bedtime_end, '%H:%M').time()
                except ValueError:
                    try:
                        bedtime_end_time = datetime.strptime(bedtime_end, '%H:%M:%S').time()
                    except ValueError:
                        logger.warning(f"Invalid bedtime end format: {bedtime_end}")
            
            # Update or create the ScreenTimeRule in the database
            rule, created = ScreenTimeRule.objects.get_or_create(device=device)
            rule.daily_limit_minutes = daily_limit_minutes
            
            if bedtime_start_time is not None:
                rule.bedtime_start = bedtime_start_time
            if bedtime_end_time is not None:
                rule.bedtime_end = bedtime_end_time
                
            # Mark as needing sync to device
            rule.synced_to_device = False
            rule.save()
            
            logger.info(f"Screen time rule {'created' if created else 'updated'} locally: {rule}")
            
            # Now sync with Android app through API
            try:
                api_response = requests.post(
                    f'{settings.API_BASE_URL}set-screen-time/',
                    headers={
                        'Authorization': f'Bearer {request.COOKIES.get("access_token")}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'device_id': device_id,
                        'daily_limit_minutes': daily_limit_minutes,
                        'bedtime_start': bedtime_start,
                        'bedtime_end': bedtime_end
                    }
                )
                logger.info(f"API sync response: {api_response.status_code} {api_response.text}")
                
                if api_response.status_code == 200:
                    success_msg = 'Screen time rules updated successfully and synced to device!'
                else:
                    success_msg = 'Screen time rules updated locally. Sync to device may have failed.'
                    logger.warning(f"API sync failed: {api_response.status_code} {api_response.text}")
                    
            except Exception as e:
                logger.exception("Error during API sync")
                success_msg = 'Screen time rules updated locally. Device sync failed.'
            
            # Return appropriate response
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({
                    'status': 'updated',
                    'message': success_msg,
                    'daily_limit_minutes': rule.daily_limit_minutes,
                    'bedtime_start': rule.bedtime_start.strftime('%H:%M') if rule.bedtime_start else None,
                    'bedtime_end': rule.bedtime_end.strftime('%H:%M') if rule.bedtime_end else None
                })
            else:
                messages.success(request, success_msg)
                return redirect('manage_device', device_id=device_id)
                
        except (ValueError, TypeError) as e:
            error_msg = f'Invalid input: {str(e)}'
            logger.error(error_msg)
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'error': error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect('manage_device', device_id=device_id)
        except Exception as e:
            error_msg = f'Failed to update screen time rules: {str(e)}'
            logger.exception(error_msg)
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'error': error_msg}, status=500)
            else:
                messages.error(request, error_msg)
                return redirect('manage_device', device_id=device_id)
    
    # Handle GET requests or invalid methods
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    else:
        return redirect('manage_device', device_id=device_id)


@csrf_exempt
@login_required
def get_blocked_apps(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    blocked_apps = device.blocked_apps.all().values_list('app_name', flat=True)
    return JsonResponse({'blocked_apps': list(blocked_apps)})


class ParentLoginView(LoginView):
    template_name = 'parent_ui/login.html'

    def form_valid(self, form):
        user = form.get_user()
        
        # Check if user's email is verified
        if not user.is_email_verified:
            messages.error(
                self.request,
                'Please verify your email address before logging in. Check your inbox for the verification email.'
            )
            # Add a link to resend verification email
            messages.info(
                self.request,
                f'<a href="/parent/resend-verification/">Click here to resend verification email</a>',
                extra_tags='safe'
            )
            return self.form_invalid(form)
        
        # Proceed with normal login
        response = super().form_valid(form)

        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        # Set cookies with proper attributes
        response.set_cookie(
            'access_token',
            access_token,
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax',
            path='/'
        )

        # Also set a session variable
        self.request.session['is_authenticated'] = True

        return response

    def get_success_url(self):
        return '/'  # Redirect to dashboard


@require_GET
def sse_events(request):
    token = request.GET.get('token')
    if not token:
        return HttpResponseForbidden("Missing token")

    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = CustomUser.objects.get(id=user_id)
        request.user = user
    except Exception as e:
        return HttpResponseForbidden(f"Invalid token: {str(e)}")

    def generate_response():
        # Get current updates
        current_time = timezone.now().isoformat()
        data = {
            'timestamp': current_time,
            'data': {'update': current_time}
        }
        return f"data: {json.dumps(data)}\n\n"

    response = StreamingHttpResponse(
        streaming_content=(generate_response(),),
        content_type='text/event-stream'
    )

    # Only set safe headers
    response['Cache-Control'] = 'no-cache'
    return response


@login_required
@require_http_methods(["GET"])
def poll_updates(request):
    # Get latest updates
    updates = {
        'timestamp': timezone.now().isoformat(),
        'data': {
            # Add your update data here
        }
    }
    return JsonResponse(updates)


def register(request):
    if request.method == 'POST':
        form = ParentRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_parent = True
            user.is_active = False  # User will be activated after email verification
            user.save()
            
            # Send verification email
            from .email_utils import send_verification_email
            if send_verification_email(user, request):
                messages.success(request, 'Registration successful! Please check your email to verify your account.')
            else:
                messages.warning(request, 'Registration successful, but we could not send the verification email. Please contact support.')
            
            return redirect('registration_success')
    else:
        form = ParentRegistrationForm()

    return render(request, 'parent_ui/register.html', {'form': form})


class RegistrationSuccessView(TemplateView):
    template_name = 'parent_ui/registration_success.html'


def verify_email(request, token):
    """Handle email verification"""
    from .email_utils import verify_email_token
    
    user, message = verify_email_token(token)
    
    if user:
        if user.is_email_verified:
            messages.success(request, message)
            # Log the user in after successful verification
            login(request, user)
            return redirect('parent_dashboard')
        else:
            messages.info(request, message)
    else:
        messages.error(request, message)
    
    return render(request, 'parent_ui/email_verification_result.html', {
        'user': user,
        'message': message
    })


def resend_verification_email(request):
    """Resend verification email"""
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            messages.error(request, 'Please provide your email address.')
            return redirect('resend_verification')
        
        try:
            from api.models import CustomUser
            user = CustomUser.objects.get(email=email, is_email_verified=False)
            
            from .email_utils import resend_verification_email as resend_email
            success, message = resend_email(user, request)
            
            if success:
                messages.success(request, message)
            else:
                messages.error(request, message)
                
        except CustomUser.DoesNotExist:
            messages.error(request, 'No unverified account found with this email address.')
        except Exception as e:
            messages.error(request, 'An error occurred. Please try again later.')
    
    return render(request, 'parent_ui/resend_verification.html')


@login_required
def account_settings(request):
    """Display and handle account settings updates."""
    user = request.user
    
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'account_info':
            form = AccountSettingsForm(request.POST, instance=user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your account information has been updated successfully.')
                return redirect('account_settings')
            else:
                messages.error(request, 'Please correct the errors below.')
        
        elif form_type == 'change_password':
            password_form = ChangePasswordForm(user, request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, user)  # Keep user logged in after password change
                messages.success(request, 'Your password has been changed successfully.')
                return redirect('account_settings')
            else:
                messages.error(request, 'Please correct the errors in the password form.')
    
    # GET request or form validation failed
    account_form = AccountSettingsForm(instance=user)
    password_form = ChangePasswordForm(user)
    
    # Get some account statistics
    devices = ChildDevice.objects.filter(parent=user)
    total_devices = devices.count()
    total_blocked_apps = BlockedApp.objects.filter(device__parent=user).count()
    total_screen_rules = ScreenTimeRule.objects.filter(device__parent=user).count()
    
    context = {
        'account_form': account_form,
        'password_form': password_form,
        'total_devices': total_devices,
        'total_blocked_apps': total_blocked_apps,
        'total_screen_rules': total_screen_rules,
        'devices': devices,
    }
    
    return render(request, 'parent_ui/account_settings.html', context)


class CustomLogoutView(LogoutView):
    """Custom logout view that clears JWT tokens and custom session data"""
    
    def dispatch(self, request, *args, **kwargs):
        # Clear custom session data
        if 'is_authenticated' in request.session:
            del request.session['is_authenticated']
        
        # Call the parent dispatch to handle Django's logout
        response = super().dispatch(request, *args, **kwargs)
        
        # Clear JWT token cookies
        if hasattr(response, 'delete_cookie'):
            response.delete_cookie('access_token', path='/')
            response.delete_cookie('refresh_token', path='/')  # In case this was set elsewhere
        
        return response


def content_blocked_view(request):
    """
    Display a simple blocked content page when inappropriate content is accessed.
    This view doesn't require authentication as it's meant to be accessible
    when parental controls block content.
    """
    # Simple static page - no need to process URLs or provide complex context
    return render(request, 'parent_ui/content_blocked_simple.html')


@login_required
def test_offline_notification(request):
    """Send a test offline notification email to the logged-in parent"""
    if request.method == 'POST':
        try:
            device_id = request.POST.get('device_id')
            
            # Log the test request
            logger.info(f"Test offline notification requested by user {request.user.email}")
            
            # Get the device if specified, otherwise use None for mock data
            device = None
            if device_id:
                try:
                    device = ChildDevice.objects.get(device_id=device_id, parent=request.user)
                    logger.info(f"Using real device: {device.nickname or device.device_id}")
                except ChildDevice.DoesNotExist:
                    logger.info(f"Device {device_id} not found, using mock data")
            else:
                logger.info("No device specified, using mock data")
            
            from .email_utils import send_test_offline_notification
            success = send_test_offline_notification(request.user, device)
            
            if success:
                logger.info(f"Test email sent successfully to {request.user.email}")
                messages.success(request, 'Test offline notification email sent successfully! Check your Gmail inbox.')
            else:
                logger.error(f"Failed to send test email to {request.user.email}")
                messages.error(request, 'Failed to send test email. Please check your email settings.')
            
            return JsonResponse({
                'success': success,
                'message': 'Test email sent successfully!' if success else 'Failed to send test email.'
            })
            
        except Exception as e:
            logger.exception(f"Error in test_offline_notification: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)