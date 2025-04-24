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

@login_required
def block_app(request, device_id):
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    if request.method == 'POST':
        form = BlockAppForm(request.POST)
        if form.is_valid():
            blocked_app = form.save(commit=False)
            blocked_app.device = device
            blocked_app.save()
            return redirect('manage_device', device_id=device_id)
    
    return redirect('parent_dashboard')


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
        
        # Set cookies
        response.set_cookie(
            'access_token',
            str(refresh.access_token),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax'
        )
        response.set_cookie(
            'refresh_token',
            str(refresh),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax'
        )
        
        return response