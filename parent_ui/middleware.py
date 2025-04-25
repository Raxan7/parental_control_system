from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings

class AuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # List of paths that don't require authentication
        exempt_paths = [
            '/login/',
            '/api/token/',
            '/static/',
            '/favicon.ico',
        ]

        # Check if the path is exempt
        if any(request.path.startswith(path) for path in exempt_paths):
            return self.get_response(request)

        # Check for authentication
        if not request.user.is_authenticated:
            return redirect('login')

        response = self.get_response(request)
        return response