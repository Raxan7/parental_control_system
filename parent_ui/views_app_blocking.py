# View for the app blocking functionality in the parent web UI
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from api.models import ChildDevice, BlockedApp, AppUsageLog
from .forms import BlockAppForm
from .tasks import send_blocked_app_notification
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def trigger_device_sync(device_id, action, app_name=None):
    """
    Helper function to trigger immediate sync on the Android device
    """
    try:
        # This would normally send a push notification
        # For now, we rely on the faster polling mechanism
        logger.info(f"Sync trigger: Device {device_id}, Action: {action}, App: {app_name}")
        
        # In a real implementation with FCM:
        # if hasattr(settings, 'FCM_SERVER_KEY'):
        #     from pyfcm import FCMNotification
        #     push_service = FCMNotification(api_key=settings.FCM_SERVER_KEY)
        #     push_service.notify_single_device(
        #         registration_id=device_id,
        #         message_title="Parental Controls Updated",
        #         message_body=f"App blocking list updated",
        #         data_message={
        #             'action': action,
        #             'app_name': app_name,
        #             'sync_required': True
        #         }
        #     )
        
        return True
    except Exception as e:
        logger.error(f"Failed to trigger device sync: {str(e)}")
        return False

@login_required
def app_blocking_view(request, device_id):
    """
    Main view for blocking and managing apps
    """
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    # Handle POST request for form-based app blocking
    if request.method == 'POST':
        form = BlockAppForm(request.POST)
        if form.is_valid():
            blocked_app = form.save(commit=False)
            blocked_app.device = device
            blocked_app.blocked_by = request.user
            blocked_app.save()

            # Send push notification to device about the new blocked app
            send_blocked_app_notification(device.device_id, blocked_app.app_name, blocked_app.package_name)
            
            # Add success message
            from django.contrib import messages
            messages.success(request, f"App '{blocked_app.app_name}' has been blocked successfully.")
            
            # Check if it's an AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'app_name': blocked_app.app_name,
                    'blocked_at': blocked_app.blocked_at.strftime('%Y-%m-%d %H:%M')
                })
            
            # For regular form submission, redirect to prevent double submission
            return redirect('app_blocking', device_id=device_id)
        # If form is invalid, continue to render the page with errors
    else:
        form = BlockAppForm()
    
    # Get all blocked apps for this device
    blocked_apps = BlockedApp.objects.filter(device=device)
    print(f"Blocked apps for device {device_id}: {blocked_apps.count()} found")
    
    # Get timeframe from request parameters (default to 7 days)
    timeframe = request.GET.get('timeframe')
    custom_days = request.GET.get('custom_days')
    
    # Get the last used timeframe from the session, or default to 'week'
    if not timeframe:
        timeframe = request.session.get('app_blocking_timeframe', 'week')
        custom_days = request.session.get('app_blocking_custom_days')
    
    # Store the current timeframe in the session for next visit
    request.session['app_blocking_timeframe'] = timeframe
    if custom_days:
        request.session['app_blocking_custom_days'] = custom_days
    
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
    else:
        # Default to week if invalid timeframe
        start_date = end_date - timezone.timedelta(days=7)
        timeframe = 'week'
        timeframe_description = "Last 7 Days"
    
    # Get recently used apps on the device for easy blocking within the timeframe
    recent_apps_data = AppUsageLog.objects.filter(
        device=device,
        start_time__gte=start_date,
        start_time__lte=end_date
    )
    
    # Get distinct app names
    recent_apps = recent_apps_data.values('app_name').distinct()
    
    # Calculate total usage time for each app
    app_usage_totals = {}
    for log in recent_apps_data:
        app_name = log.app_name
        # Calculate duration in minutes
        if log.end_time:
            duration = (log.end_time - log.start_time).total_seconds() / 60
        else:
            # If end_time is None, use current time
            duration = (timezone.now() - log.start_time).total_seconds() / 60
        
        if app_name in app_usage_totals:
            app_usage_totals[app_name] += duration
        else:
            app_usage_totals[app_name] = duration
    
    # Prepare app data for the template with blocked status
    app_data = []
    blocked_package_names = set([app.package_name for app in blocked_apps if app.package_name])
    blocked_app_names = set([app.app_name for app in blocked_apps])
    
    # Check if any apps were blocked during the selected timeframe
    recently_blocked_apps = BlockedApp.objects.filter(
        device=device,
        blocked_at__gte=start_date,
        blocked_at__lte=end_date
    ).values_list('app_name', flat=True)
    
    recently_blocked_set = set(recently_blocked_apps)
    
    for app in recent_apps:
        app_name = app['app_name']
        # Check if app is blocked
        is_blocked = (app_name in blocked_app_names or 
                    app_name in blocked_package_names)
        
        # Check if app was recently blocked (within the selected timeframe)
        recently_blocked = app_name in recently_blocked_set
        
        # Get usage time (in minutes)
        usage_time = app_usage_totals.get(app_name, 0)
        
        # Format usage time
        if usage_time < 60:
            formatted_usage = f"{int(usage_time)} min"
        else:
            hours = usage_time / 60
            formatted_usage = f"{hours:.1f} hrs"
        
        app_data.append({
            'name': app_name,
            'is_blocked': is_blocked,
            'recently_blocked': recently_blocked,
            'usage_time': usage_time,  # Raw minutes for sorting
            'formatted_usage': formatted_usage,  # For display
        })
    
    # Sort apps by usage time (most used first)
    app_data.sort(key=lambda x: x['usage_time'], reverse=True)
    
    # Calculate usage statistics
    total_usage_minutes = sum(app['usage_time'] for app in app_data)
    if total_usage_minutes > 0:
        # Format total usage time
        if total_usage_minutes < 60:
            total_usage_formatted = f"{int(total_usage_minutes)} minutes"
        else:
            total_usage_hours = total_usage_minutes / 60
            total_usage_formatted = f"{total_usage_hours:.1f} hours"
            
        # Calculate daily average
        days_in_timeframe = (end_date - start_date).days
        if days_in_timeframe < 1:
            days_in_timeframe = 1  # Avoid division by zero
            
        daily_avg_minutes = total_usage_minutes / days_in_timeframe
        if daily_avg_minutes < 60:
            daily_avg_formatted = f"{int(daily_avg_minutes)} minutes"
        else:
            daily_avg_hours = daily_avg_minutes / 60
            daily_avg_formatted = f"{daily_avg_hours:.1f} hours"
    else:
        total_usage_formatted = "0 minutes"
        daily_avg_formatted = "0 minutes"
    
    context = {
        'device': device,
        'blocked_apps': blocked_apps,
        'apps': app_data,
        'timeframe': timeframe,
        'custom_days': custom_days,
        'timeframe_description': timeframe_description,
        'total_usage': total_usage_formatted,
        'daily_avg_usage': daily_avg_formatted,
        'block_app_form': form
    }
    
    return render(request, 'parent_ui/app_blocking.html', context)

@login_required
@require_POST
def toggle_block_app(request, device_id):
    """
    Endpoint to block or unblock an app quickly - supports both AJAX and form POST
    """
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    app_name = request.POST.get('app_name')
    package_name = request.POST.get('package_name', '')
    action = request.POST.get('action', 'block')  # block or unblock
    
    # Determine if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if not app_name:
        if is_ajax:
            return JsonResponse({'status': 'error', 'message': 'App name is required'}, status=400)
        else:
            # For form submissions, redirect back with error message
            messages.error(request, 'App name is required')
            return redirect('app_blocking', device_id=device_id)
    
    try:
        if action == 'block':
            # Check if app is already blocked by app_name (primary identifier)
            existing_block = BlockedApp.objects.filter(
                device=device, 
                app_name=app_name,
                is_active=True
            ).first()
            
            if existing_block:
                message = f'{app_name} is already blocked'
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'message': message,
                        'action': 'block',
                        'app_id': existing_block.id
                    })
                else:
                    messages.info(request, message)
                    return redirect('app_blocking', device_id=device_id)
            
            # Create new blocked app entry - quick block similar to form
            blocked_app = BlockedApp.objects.create(
                device=device,
                app_name=app_name,
                package_name=package_name if package_name else app_name,  # Use app_name as fallback
                blocked_by=request.user,
                is_active=True
            )
            
            # Trigger device sync for immediate effect
            trigger_device_sync(device.device_id, 'block', app_name)
            
            logger.info(f"Quick blocked app: {app_name} for device {device_id}")
            
            message = f'{app_name} has been blocked successfully'
            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': message,
                    'action': 'block',
                    'app_id': blocked_app.id
                })
            else:
                messages.success(request, message)
                return redirect('app_blocking', device_id=device_id)
            
        elif action == 'unblock':
            # Find and DELETE the specific blocked app entry by app_name
            blocked_apps = BlockedApp.objects.filter(
                device=device, 
                app_name=app_name,
                is_active=True
            )
            
            if blocked_apps.exists():
                # Delete all matching blocked app entries for this app
                deleted_count = 0
                for blocked_app in blocked_apps:
                    blocked_app_id = blocked_app.id
                    blocked_app.delete()  # Completely remove from database
                    deleted_count += 1
                
                trigger_device_sync(device.device_id, 'unblock', app_name)
                
                logger.info(f"Deleted {deleted_count} blocked app entries for: {app_name} on device {device_id}")
                
                message = f'{app_name} has been unblocked and removed from blocked apps'
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'message': message,
                        'action': 'unblock',
                        'deleted_count': deleted_count
                    })
                else:
                    messages.success(request, message)
                    return redirect('app_blocking', device_id=device_id)
            else:
                message = f'{app_name} is not currently blocked'
                if is_ajax:
                    return JsonResponse({
                        'status': 'error',
                        'message': message,
                        'action': 'unblock'
                    }, status=400)
                else:
                    messages.warning(request, message)
                    return redirect('app_blocking', device_id=device_id)
        
        else:
            message = f'Invalid action: {action}'
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': message,
                }, status=400)
            else:
                messages.error(request, message)
                return redirect('app_blocking', device_id=device_id)
            
    except Exception as e:
        logger.exception(f"Error in toggle_block_app for {action} action on {app_name}: {str(e)}")
        message = f'Failed to {action} app: {str(e)}'
        if is_ajax:
            return JsonResponse({
                'status': 'error',
                'message': message,
            }, status=500)
        else:
            messages.error(request, message)
            return redirect('app_blocking', device_id=device_id)