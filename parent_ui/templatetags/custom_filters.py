from django import template
from django.utils.safestring import mark_safe
from ..models import AppIcon, CustomAppMapping  # Import your app models

register = template.Library()

@register.filter
def div(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return None

@register.filter
def friendly_app_name(package_name, user=None):
    """
    Convert package names like 'com.whatsapp' to 'WhatsApp'
    Supports custom app names defined by parents
    """
    # First check for custom mappings if user is provided
    if user:
        try:
            custom_mapping = CustomAppMapping.objects.get(parent=user, package_name=package_name)
            return custom_mapping.custom_name
        except CustomAppMapping.DoesNotExist:
            pass
    
    # Check for app icons in the database
    try:
        app_icon = AppIcon.objects.get(package_name=package_name)
        return app_icon.friendly_name
    except AppIcon.DoesNotExist:
        pass
    
    # If no custom mapping or app icon, use predefined mappings
    # Common app mappings
    app_mappings = {
        # Social Media
        'com.whatsapp': 'WhatsApp',
        'com.facebook.katana': 'Facebook',
        'com.instagram.android': 'Instagram',
        'com.snapchat.android': 'Snapchat',
        'com.twitter.android': 'Twitter',
        'com.discord': 'Discord',
        'org.telegram.messenger': 'Telegram',
        'com.zhiliaoapp.musically': 'TikTok',
        'com.reddit.frontpage': 'Reddit',
        'com.linkedin.android': 'LinkedIn',
        
        # Messaging
        'com.google.android.gm': 'Gmail',
        'com.microsoft.office.outlook': 'Outlook',
        
        # Games
        'com.mojang.minecraftpe': 'Minecraft',
        'com.roblox.client': 'Roblox',
        'com.supercell.clashroyale': 'Clash Royale',
        'com.supercell.clashofclans': 'Clash of Clans',
        'com.king.candycrushsaga': 'Candy Crush Saga',
        
        # Other
        'com.android.chrome': 'Chrome',
        'com.google.android.youtube': 'YouTube',
        'com.amazon.mShop.android.shopping': 'Amazon',
        'com.spotify.music': 'Spotify',
        'com.netflix.mediaclient': 'Netflix'
    }
    
    # Try to get from predefined mappings
    if package_name in app_mappings:
        return app_mappings[package_name]
    
    # If all else fails, format the package name
    parts = package_name.split('.')
    if len(parts) > 1:
        app_name = parts[-1].replace('_', ' ').title()
        return app_name
    
    return package_name

@register.filter
def minutes_to_hours(minutes):
    """
    Convert minutes to hours
    """
    try:
        return float(minutes) / 60.0
    except (ValueError, ZeroDivisionError):
        return 0.0
