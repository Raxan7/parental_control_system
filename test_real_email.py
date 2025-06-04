#!/usr/bin/env python
"""
Test email sending functionality with real SMTP
"""
import os
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

from django.core.mail import send_mail
from django.conf import settings

def test_email_sending():
    """Test sending a real email"""
    print("📧 Testing Real Email Sending")
    print("=" * 50)
    
    # Test email details
    test_email = "manyerere201@gmail.com"  # Send to yourself for testing
    subject = "Test Email from Parental Control System"
    message = f"""
Hello,

This is a test email from the Parental Control System to verify that email sending is working correctly.

Test Details:
- Sent at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- Backend: {settings.EMAIL_BACKEND}
- Host: {settings.EMAIL_HOST}
- Port: {settings.EMAIL_PORT}
- TLS: {settings.EMAIL_USE_TLS}
- From: {settings.EMAIL_HOST_USER}

If you received this email, the email configuration is working properly!

Best regards,
Parental Control System
"""
    
    print(f"Sending test email to: {test_email}")
    print(f"Email backend: {settings.EMAIL_BACKEND}")
    print(f"SMTP host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    print(f"From email: {settings.EMAIL_HOST_USER}")
    print(f"Using TLS: {settings.EMAIL_USE_TLS}")
    
    try:
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        if result == 1:
            print("✅ Email sent successfully!")
            print(f"📧 Check the inbox for: {test_email}")
        else:
            print("❌ Email sending failed - no emails were sent")
            
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        print("🔧 Common issues:")
        print("   - Check Gmail App Password is correct")
        print("   - Ensure 2-Factor Authentication is enabled on Gmail")
        print("   - Verify Less Secure Apps setting (if using regular password)")
        print("   - Check internet connection")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Email test completed!")
    
    return True

if __name__ == "__main__":
    test_email_sending()
