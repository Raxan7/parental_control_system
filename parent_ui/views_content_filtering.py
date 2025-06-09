# parent_ui/views_content_filtering.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from api.models import ChildDevice

@login_required
def ai_content_filtering_view(request, device_id):
    """
    AI content filtering information page
    """
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    context = {
        'device': device,
    }
    
    return render(request, 'parent_ui/ai_content_filtering.html', context)

@login_required
@require_http_methods(["GET"])
def get_ai_status(request, device_id):
    """
    Get AI status - always active since it runs on device
    """
    device = get_object_or_404(ChildDevice, device_id=device_id, parent=request.user)
    
    status_data = {
        'status': 'active',
        'message': 'Content filtering is active on device'
    }
    
    return JsonResponse(status_data)
