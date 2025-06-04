#!/usr/bin/env python
"""
Test user registration with real email sending
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

def test_registration_with_real_email():
    """Test registration with real email verification"""
    print("🔐 Testing Registration with Real Email Verification")
    print("=" * 60)
    
    client = Client()
    
    # Create test data
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    test_data = {
        'username': f'realtest_{timestamp}',
        'email': 'manyerere201@gmail.com',  # Use real email for testing
        'password1': 'testpassword123',
        'password2': 'testpassword123',
        'first_name': 'Real',
        'last_name': 'Test'
    }
    
    print(f"1. Registering user: {test_data['username']}")
    print(f"   Email: {test_data['email']}")
    
    # Test registration
    response = client.post('/register/', test_data)
    
    if response.status_code == 302:
        print("✅ Registration successful!")
        print(f"📍 Redirected to: {response.url}")
        
        # Check if user was created
        try:
            user = User.objects.get(username=test_data['username'])
            print(f"✅ User created: {user.username}")
            print(f"📧 Email: {user.email}")
            print(f"🔓 Active: {user.is_active}")
            print(f"✉️  Email verified: {user.is_email_verified}")
            print(f"🎟️  Verification token: {user.email_verification_token}")
            
            print("\n📧 IMPORTANT: Check your email inbox!")
            print("   A verification email should have been sent to: manyerere201@gmail.com")
            print("   The email will contain a verification link you can click.")
            
            # Show the verification URL that would be in the email
            verification_url = f"http://127.0.0.1:8000/verify-email/{user.email_verification_token}/"
            print(f"\n🔗 Manual verification URL (if needed):")
            print(f"   {verification_url}")
            
        except User.DoesNotExist:
            print("❌ User not found in database")
            return False
            
    else:
        print(f"❌ Registration failed with status: {response.status_code}")
        if hasattr(response, 'context') and response.context and 'form' in response.context:
            form = response.context['form']
            if form.errors:
                print(f"📝 Form errors: {form.errors}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Registration with real email test completed!")
    print("📧 Please check your email and click the verification link.")
    
    return True

if __name__ == "__main__":
    test_registration_with_real_email()
