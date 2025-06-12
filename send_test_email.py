#!/usr/bin/env python
"""
Standalone script to send a test offline device notification email.
This script can be run independently to test email functionality.
"""

import os
import sys
import django
from datetime import timedelta

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from api.models import CustomUser, ChildDevice


def send_test_offline_notification_email(recipient_email, device_name=None, device_id=None):
    """Send a test offline notification email"""
    try:
        # Use provided device info or create mock data
        if not device_name:
            device_name = "Sample Child Device"
        if not device_id:
            device_id = "sample_device_123"
        
        # Create mock data for the email
        last_sync = timezone.now() - timedelta(days=3)
        
        # Email context with test data
        context = {
            'parent_name': recipient_email.split('@')[0],  # Use email username as parent name
            'device_name': device_name,
            'device_id': device_id,
            'days_offline': 3,
            'last_sync': last_sync,
            'last_sync_date': last_sync.strftime('%Y-%m-%d %H:%M') if last_sync else 'Never',
            'site_name': 'Parental Control System',
            'is_test': True,  # Flag to indicate this is a test email
        }
        
        # Render email templates
        html_message = render_to_string('parent_ui/emails/device_offline_notification.html', context)
        plain_message = render_to_string('parent_ui/emails/device_offline_notification.txt', context)
        
        # Send email with test prefix
        send_mail(
            subject=f'[TEST] Device Alert: {device_name} has been offline for 3 days',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Test offline notification email sent successfully to {recipient_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test offline notification email: {str(e)}")
        return False


def send_test_with_real_device(recipient_email):
    """Send test email using a real device from the database if available"""
    try:
        # Try to find a parent user
        user = CustomUser.objects.filter(email=recipient_email).first()
        if not user:
            # Find any parent user
            user = CustomUser.objects.filter(is_parent=True).first()
        
        if user:
            # Try to find a device for this user
            device = ChildDevice.objects.filter(parent=user).first()
            if device:
                print(f"📱 Using real device: {device.nickname or device.device_id}")
                return send_test_offline_notification_email(
                    recipient_email, 
                    device.nickname or device.device_id, 
                    device.device_id
                )
        
        # Fall back to mock data
        print("📱 Using mock device data")
        return send_test_offline_notification_email(recipient_email)
        
    except Exception as e:
        print(f"❌ Error accessing database: {str(e)}")
        return send_test_offline_notification_email(recipient_email)


def main():
    """Main function to run the test"""
    print("🚀 Starting test offline device notification email...")
    print(f"📧 Email backend: {settings.EMAIL_BACKEND}")
    print(f"📤 From email: {settings.DEFAULT_FROM_EMAIL}")
    print(f"🔑 Using email host: {settings.EMAIL_HOST_USER}")
    
    # Check if email password is configured
    if not settings.EMAIL_HOST_PASSWORD:
        print("⚠️  Warning: EMAIL_HOST_PASSWORD is not set in environment variables!")
        print("   Make sure you have set EMAIL_HOST_PASSWORD in your .env file")
        return False
    
    # Target email
    recipient_email = "manyerere201@gmail.com"
    print(f"📨 Sending test email to: {recipient_email}")
    
    # Send the test email
    success = send_test_with_real_device(recipient_email)
    
    if success:
        print("\n✅ Test completed successfully!")
        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            print("📺 Email was sent to console (check terminal output above)")
        else:
            print(f"📧 Email was sent via SMTP to {recipient_email}")
            print("📬 Check your Gmail inbox (including spam folder)")
    else:
        print("\n❌ Test failed!")
        print("💡 Troubleshooting tips:")
        print("   - Check your Gmail app password is correct")
        print("   - Ensure 2-factor authentication is enabled on Gmail")
        print("   - Verify the app password in .env file")
    
    return success


if __name__ == "__main__":
    main()
