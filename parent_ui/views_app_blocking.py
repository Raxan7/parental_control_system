# View for the app blocking functionality in the parent web UI
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from api.models import ChildDevice, BlockedApp, AppUsageLog
from .forms import BlockAppForm
from .tasks import send_blocked_app_notification
import logging

logger = logging.getLogger(__name__)

@login_required
def app_blocking_view(request, device_id):
    """
    Main view for blocking and managing apps
    """
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    # Get all blocked apps for this device
    blocked_apps = BlockedApp.objects.filter(device=device)
    
    # Get recently used apps on the device for easy blocking
    recent_apps = AppUsageLog.objects.filter(
        device=device
    ).values('app_name').distinct()
    
    # Prepare app data for the template with blocked status
    app_data = []
    blocked_package_names = set([app.package_name for app in blocked_apps if app.package_name])
    blocked_app_names = set([app.app_name for app in blocked_apps])
    
    for app in recent_apps:
        app_name = app['app_name']
        # Check if app is blocked
        is_blocked = (app_name in blocked_app_names or 
                    app_name in blocked_package_names)
        
        app_data.append({
            'name': app_name,
            'is_blocked': is_blocked,
        })
    
    # Sort apps by name
    app_data.sort(key=lambda x: x['name'])
    
    context = {
        'device': device,
        'blocked_apps': blocked_apps,
        'apps': app_data,
        'block_app_form': BlockAppForm()
    }
    
    return render(request, 'parent_ui/app_blocking.html', context)

@login_required
@require_POST
def toggle_block_app(request, device_id):
    """
    AJAX endpoint to block or unblock an app
    """
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    app_name = request.POST.get('app_name')
    package_name = request.POST.get('package_name', '')
    action = request.POST.get('action', 'block')  # block or unblock
    
    if not app_name:
        return JsonResponse({'status': 'error', 'message': 'App name is required'}, status=400)
    
    try:
        if action == 'block':
            # Check if app is already blocked
            existing_block = BlockedApp.objects.filter(
                device=device, 
                app_name=app_name
            ).first()
            
            if existing_block:
                # If already blocked, just return success
                return JsonResponse({
                    'status': 'success',
                    'message': f'{app_name} is already blocked',
                    'action': 'block'
                })
            
            # Create new blocked app entry
            blocked_app = BlockedApp.objects.create(
                device=device,
                app_name=app_name,
                package_name=package_name,
                blocked_by=request.user
            )
            
            # Send notification to device
            send_blocked_app_notification.delay(device.device_id, app_name, package_name)
            
            return JsonResponse({
                'status': 'success',
                'message': f'{app_name} has been blocked',
                'action': 'block',
                'app_id': blocked_app.id
            })
            
        elif action == 'unblock':
            # Find and delete the blocked app entry
            blocked_app = BlockedApp.objects.filter(
                device=device, 
                app_name=app_name
            ).first()
            
            if blocked_app:
                blocked_app_id = blocked_app.id
                blocked_app.delete()
                
                return JsonResponse({
                    'status': 'success',
                    'message': f'{app_name} has been unblocked',
                    'action': 'unblock',
                    'app_id': blocked_app_id
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': f'{app_name} is not currently blocked',
                    'action': 'unblock'
                }, status=400)
        
        else:
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid action: {action}',
            }, status=400)
            
    except Exception as e:
        logger.exception(f"Error in toggle_block_app: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to {action} app: {str(e)}',
        }, status=500)