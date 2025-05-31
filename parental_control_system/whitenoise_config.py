# WhiteNoise configuration for proper MIME types
from whitenoise import WhiteNoise
from django.conf import settings
import mimetypes

# Add custom MIME types
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/woff2', '.woff2')
mimetypes.add_type('application/font-woff', '.woff')
mimetypes.add_type('application/font-woff2', '.woff2')

class CustomWhiteNoise(WhiteNoise):
    """Custom WhiteNoise class with proper MIME type handling"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure proper MIME types
        self.add_mime_types()
    
    def add_mime_types(self):
        """Add custom MIME types"""
        self.mime_types.update({
            '.js': 'application/javascript',
            '.css': 'text/css',
            '.svg': 'image/svg+xml',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject',
        })
