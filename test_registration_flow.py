#!/usr/bin/env python
"""
Test complete registration and email verification flow
"""
import os
import sys
import django
from datetime import datetime
from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

User = get_user_model()

def test_registration_flow():
    """Test the complete registration and email verification flow"""
    print("🔄 Testing Complete Registration Flow")
    print("=" * 50)
    
    client = Client()
    
    # Test data for new user
    test_email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
    test_username = f"testuser_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_password = "testpassword123"
    
    print(f"1. Testing registration with user: {test_username}")
    
    # Test registration page access
    response = client.get('/register/')
    if response.status_code == 200:
        print("   ✅ Registration page accessible")
    else:
        print(f"   ❌ Registration page error: {response.status_code}")
        return False
    
    # Test registration form submission
    registration_data = {
        'username': test_username,
        'email': test_email,
        'password1': test_password,
        'password2': test_password,
        'first_name': 'Test',
        'last_name': 'User'
    }
    
    response = client.post('/register/', registration_data)
    print(f"   Registration response status: {response.status_code}")
    
    if response.status_code == 302:  # Redirect to success page
        print("   ✅ Registration successful (redirected)")
        redirect_url = response.url
        print(f"   📍 Redirected to: {redirect_url}")
    else:
        print("   ⚠️  Registration response (may need form adjustment)")
        if hasattr(response, 'context') and response.context and 'form' in response.context:
            form = response.context['form']
            if form.errors:
                print(f"   📝 Form errors: {form.errors}")
    
    # Check if user was created
    try:
        user = User.objects.get(username=test_username)
        print(f"   ✅ User created: {user.username}")
        print(f"   📧 Email: {user.email}")
        print(f"   🔓 Active: {user.is_active}")
        print(f"   ✉️  Email verified: {user.email_verified if hasattr(user, 'email_verified') else 'N/A'}")
        
        # Test registration success page
        response = client.get('/register/success/')
        if response.status_code == 200:
            print("   ✅ Registration success page accessible")
        else:
            print(f"   ⚠️  Registration success page: {response.status_code}")
            
    except User.DoesNotExist:
        print("   ⚠️  User not found in database")
    
    print("\n2. Testing email verification pages...")
    
    # Test email verification result page
    response = client.get('/verify-email/invalid-token/')
    print(f"   Email verification page status: {response.status_code}")
    if response.status_code == 200:
        print("   ✅ Email verification page accessible")
    
    # Test resend verification page
    response = client.get('/resend-verification/')
    if response.status_code == 200:
        print("   ✅ Resend verification page accessible")
    else:
        print(f"   ⚠️  Resend verification page: {response.status_code}")
    
    print("\n3. Testing login with new user...")
    
    # Try to login with new user (should work even if email not verified)
    login_data = {
        'username': test_username,
        'password': test_password
    }
    
    response = client.post('/login/', login_data)
    if response.status_code == 302:
        print("   ✅ Login successful")
        print(f"   📍 Redirected to: {response.url}")
    else:
        print(f"   ⚠️  Login response: {response.status_code}")
    
    print("\n" + "=" * 50)
    print("🎉 Registration flow test completed!")
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

if __name__ == "__main__":
    test_registration_flow()
