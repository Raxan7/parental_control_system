#!/usr/bin/env python
"""
Test resend verification email functionality
"""
import os
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

def test_resend_verification():
    """Test resending verification email"""
    print("📤 Testing Resend Verification Email")
    print("=" * 50)
    
    client = Client()
    
    # Find an unverified user
    unverified_user = User.objects.filter(is_email_verified=False).first()
    
    if not unverified_user:
        print("❌ No unverified users found for testing")
        return False
    
    print(f"📧 Testing with user: {unverified_user.username}")
    print(f"   Email: {unverified_user.email}")
    print(f"   Currently verified: {unverified_user.is_email_verified}")
    
    # Test resend verification page
    response = client.get('/resend-verification/')
    
    if response.status_code == 200:
        print("✅ Resend verification page accessible")
        
        # Test posting to resend verification
        resend_data = {
            'email': unverified_user.email
        }
        
        post_response = client.post('/resend-verification/', resend_data)
        
        if post_response.status_code in [200, 302]:
            print("✅ Resend verification email request processed")
            print("📧 Check your email - a new verification email should be sent!")
            
            # Show the verification URL
            verification_url = f"http://127.0.0.1:8000/verify-email/{unverified_user.email_verification_token}/"
            print(f"\n🔗 Verification URL:")
            print(f"   {verification_url}")
            
        else:
            print(f"❌ Resend failed with status: {post_response.status_code}")
            return False
            
    else:
        print(f"❌ Resend verification page failed: {response.status_code}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 Resend verification test completed!")
    
    return True

if __name__ == "__main__":
    test_resend_verification()
