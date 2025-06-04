#!/usr/bin/env python3

"""
Test script to validate the complete authentication workflow
"""

import os
import sys
import django
import requests
from datetime import datetime

# Add the project directory to Python path
project_path = r'c:\Users\Hussein\Desktop\FINAL_PROJECT\NEW_FOLDER\FYP\parental_control_system'
sys.path.append(project_path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

from django.test import Client
from django.contrib.auth import authenticate
from api.models import CustomUser

def test_authentication_workflow():
    """Test the complete authentication workflow"""
    print("🔐 Testing Authentication Workflow")
    print("=" * 50)
    
    # Test 1: Check if test user exists and is properly configured
    print("\n1. Checking test user status...")
    try:
        user = CustomUser.objects.get(username='testuser')
        print(f"   ✅ Test user exists: {user.username}")
        print(f"   ✅ Email verified: {user.is_email_verified}")
        print(f"   ✅ User active: {user.is_active}")
        print(f"   ✅ Is parent: {user.is_parent}")
    except CustomUser.DoesNotExist:
        print("   ❌ Test user not found!")
        return False
    
    # Test 2: Test Django authentication
    print("\n2. Testing Django authentication...")
    auth_user = authenticate(username='testuser', password='testpass123')
    if auth_user:
        print("   ✅ Django authentication successful")
    else:
        print("   ❌ Django authentication failed")
        return False
    
    # Test 3: Test login page accessibility
    print("\n3. Testing page accessibility...")
    client = Client()
    
    # Test login page
    response = client.get('/login/')
    if response.status_code == 200:
        print("   ✅ Login page accessible")
    else:
        print(f"   ❌ Login page error: {response.status_code}")
        return False
    
    # Test register page
    response = client.get('/register/')
    if response.status_code == 200:
        print("   ✅ Register page accessible")
    else:
        print(f"   ❌ Register page error: {response.status_code}")
        return False
    
    # Test resend verification page
    response = client.get('/resend-verification/')
    if response.status_code == 200:
        print("   ✅ Resend verification page accessible")
    else:
        print(f"   ❌ Resend verification page error: {response.status_code}")
        return False
    
    # Test 4: Test actual login workflow
    print("\n4. Testing login workflow...")
    response = client.post('/login/', {
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    if response.status_code == 302:  # Redirect after successful login
        print("   ✅ Login successful (redirected)")
        print(f"   ✅ Redirect location: {response.get('Location', 'Unknown')}")
    else:
        print(f"   ❌ Login failed: {response.status_code}")
        return False
    
    # Test 5: Test dashboard access after login
    print("\n5. Testing dashboard access...")
    response = client.get('/')
    if response.status_code == 200:
        print("   ✅ Dashboard accessible after login")
    else:
        print(f"   ❌ Dashboard access error: {response.status_code}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 All authentication tests passed!")
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

def test_template_rendering():
    """Test that all templates render without errors"""
    print("\n🎨 Testing Template Rendering")
    print("=" * 50)
    
    client = Client()
    
    pages_to_test = [
        ('/login/', 'Login Page'),
        ('/register/', 'Register Page'),
        ('/resend-verification/', 'Resend Verification Page'),
        ('/register/success/', 'Registration Success Page'),
    ]
    
    all_passed = True
    
    for url, name in pages_to_test:
        try:
            response = client.get(url)
            if response.status_code == 200:
                print(f"   ✅ {name}: OK")
            else:
                print(f"   ❌ {name}: Error {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"   ❌ {name}: Exception - {str(e)}")
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    success = True
    
    # Run authentication tests
    success &= test_authentication_workflow()
    
    # Run template tests
    success &= test_template_rendering()
    
    if success:
        print("\n🌟 ALL TESTS PASSED! 🌟")
        print("The login system is working correctly!")
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
        sys.exit(1)
