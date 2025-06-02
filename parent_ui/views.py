from datetime import timedelta
import json
import logging
import time
import requests

from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core import serializers
from django.http import HttpResponseForbidden, JsonResponse, StreamingHttpResponse
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


from django.db.models import Sum
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
from datetime import datetime

@login_required
def manage_device(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    # Get usage data for this specific device only
    logs = AppUsageLog.objects.filter(
        device=device
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

    # Check if PDF download was requested
    if request.GET.get('download') == 'pdf':
        return generate_pdf_report(device, logs)

    return render(request, 'parent_ui/manage_device.html', context={
        'form': form,
        'device': device,
        'screen_time_form': screen_time_form,
        'block_app_form': BlockAppForm(),
        'logs': logs,
        'usage_by_app': usage_by_app,
        'daily_usage': daily_usage,
    })

def generate_pdf_report(device, logs):
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # PDF content
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"Device Usage Report: {device.nickname or device.device_id}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # Table headers
    p.drawString(100, 750, "App Name")
    p.drawString(300, 750, "Start Time")
    p.drawString(400, 750, "Duration (mins)")
    
    # Table rows
    y = 730
    for log in logs.order_by('-start_time')[:50]:  # Limit to 50 most recent logs
        p.drawString(100, y, log.app_name)
        p.drawString(300, y, log.start_time.strftime('%Y-%m-%d %H:%M'))
        p.drawString(400, y, f"{round(log.duration/60, 1)}")
        y -= 20
        if y < 50:  # Prevent running off the page
            p.showPage()
            y = 750
    
    # Summary
    p.showPage()
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, "Usage Summary (Last 7 Days)")
    
    total_usage = sum(log.duration for log in logs)
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Total screen time: {round(total_usage/3600, 2)} hours")
    p.drawString(100, 750, f"Number of app sessions: {logs.count()}")
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{device.device_id}_usage_report.pdf"'
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
    logger.info(f"Received AJAX request to update screen time for device {device_id} by user {request.user}")

    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    if request.method == 'POST' and request.headers.get('Content-Type') == 'application/json':
        try:
            data = json.loads(request.body)
            logger.debug(f"Received JSON data: {data}")
            
            daily_limit_minutes = data.get('daily_limit_minutes')
            bedtime_start = data.get('bedtime_start')
            bedtime_end = data.get('bedtime_end')
            
            if not daily_limit_minutes:
                return JsonResponse({'error': 'daily_limit_minutes is required'}, status=400)
            
            try:
                response = requests.post(
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
                logger.info(f"API Response: {response.status_code} {response.text}")
                
                if response.status_code == 200:
                    return JsonResponse({'status': 'updated'})
                else:
                    return JsonResponse({'error': 'Failed to update screen time rules'}, status=400)
            except Exception as e:
                logger.exception("Error during API call")
                return JsonResponse({'error': str(e)}, status=500)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
@login_required
def get_blocked_apps(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    blocked_apps = device.blocked_apps.all().values_list('app_name', flat=True)
    return JsonResponse({'blocked_apps': list(blocked_apps)})


class ParentLoginView(LoginView):
    template_name = 'parent_ui/login.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        user = form.get_user()

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
            user = form.save()
            user.is_parent = True
            user.save()
            login(request, user)
            return redirect('registration_success')
    else:
        form = ParentRegistrationForm()

    return render(request, 'parent_ui/register.html', {'form': form})


class RegistrationSuccessView(TemplateView):
    template_name = 'parent_ui/registration_success.html'


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