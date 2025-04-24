# api/middleware.py
class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Skip for login and other auth views
        if request.path.startswith('/api/token/') or request.path.startswith('/admin/'):
            return None
            
        # Check for token in cookies or headers
        token = request.COOKIES.get('access_token') or request.headers.get('Authorization', '').split(' ')[-1]
        
        if token:
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                request.user = jwt_auth.get_user(validated_token)
            except Exception as e:
                pass
                
        return None
    

# api/middleware.py
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.http import JsonResponse

class JWTMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip for auth endpoints
        if request.path.startswith('/api/token/'):
            return self.get_response(request)

        # Check for token in cookies
        token = request.COOKIES.get('access_token')
        if token:
            try:
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(token)
                request.user = jwt_auth.get_user(validated_token)
                print(f"Authenticated user: {request.user}")
            except InvalidToken as e:
                print(f"Invalid token: {str(e)}")
                return JsonResponse({'error': 'Invalid token'}, status=401)

        return self.get_response(request)