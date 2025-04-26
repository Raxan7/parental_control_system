from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from api.models import ChildDevice, AppUsageLog, BlockedApp, ScreenTimeRule
from django.utils import timezone
from datetime import timedelta
import json

from parental_control_system import settings
from .forms import DeviceForm, ScreenTimeRuleForm, BlockAppForm  # Add this import
from django.utils.decorators import method_decorator
import logging

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

        # Get usage data for the last 7 days
        usage_data = []
        for device in context['devices']:
            logs = AppUsageLog.objects.filter(
                device=device,
                start_time__gte=timezone.now() - timedelta(days=7)
            )
            usage_data.append({
                'device': device,
                'logs': logs
            })
        # device = self.request.user.child_devices.first()
        # context['device'] = device
        context['block_app_form'] = BlockAppForm()
        
        context['usage_data'] = usage_data
        context['blocked_apps'] = BlockedApp.objects.filter(device__parent=user)
        context['screen_rules'] = ScreenTimeRule.objects.filter(device__parent=user)
        
        return context
    

from django.http import StreamingHttpResponse
import time

def event_stream(request):
    def event_generator():
        while True:
            # Check for new data
            time.sleep(5)
            yield f"data: {json.dumps({'update': timezone.now()})}\n\n"
    
    return StreamingHttpResponse(event_generator(), content_type='text/event-stream')


@login_required
def manage_device(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    if request.method == 'POST':
        form = DeviceForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            return redirect('parent_dashboard')
    else:
        form = DeviceForm(instance=device)
    
    return render(request, 'parent_ui/manage_device.html', {
        'form': form,
        'device': device,
        'screen_time_form': ScreenTimeRuleForm(),
        'block_app_form': BlockAppForm()
    })

@login_required
def update_screen_time(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    if request.method == 'POST':
        form = ScreenTimeRuleForm(request.POST)
        if form.is_valid():
            ScreenTimeRule.objects.update_or_create(
                device=device,
                defaults=form.cleaned_data
            )
            return redirect('manage_device', device_id=device_id)
    
    return redirect('parent_dashboard')


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core import serializers
import json

@login_required
def block_app(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    if request.method == 'POST':
        form = BlockAppForm(request.POST)
        if form.is_valid():
            blocked_app = form.save(commit=False)
            blocked_app.device = device
            blocked_app.save()
            
            # Send push notification to device about the new blocked app
            from .tasks import send_blocked_app_notification
            send_blocked_app_notification.delay(device.device_id, blocked_app.app_name)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'app_name': blocked_app.app_name,
                    'blocked_at': blocked_app.blocked_at.strftime('%Y-%m-%d %H:%M')
                })
            return redirect('manage_device', device_id=device_id)
    
    return redirect('parent_dashboard')

@csrf_exempt
@login_required
def get_blocked_apps(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    blocked_apps = device.blocked_apps.all().values_list('app_name', flat=True)
    return JsonResponse({'blocked_apps': list(blocked_apps)})


from django.contrib.auth.views import LoginView

# parent_ui/views.py
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import RefreshToken

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
    

from django.http import JsonResponse
from rest_framework_simplejwt.tokens import AccessToken
from django.http import HttpResponseForbidden
from api.models import CustomUser
from django.views.decorators.http import require_GET

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


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

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