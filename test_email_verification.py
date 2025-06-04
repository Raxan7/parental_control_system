#!/usr/bin/env python
"""
Test email verification link extraction and verification process
"""
import os
import sys
import django
import re
from datetime import datetime
from django.test import Client
from django.contrib.auth import get_user_model

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

from api.models import CustomUser

User = get_user_model()

def test_email_verification():
    """Test email verification process"""
    print("📧 Testing Email Verification Process")
    print("=" * 50)
    
    # Find the most recent user
    try:
        recent_user = User.objects.filter(username__startswith='testuser_').order_by('-date_joined').first()
        if not recent_user:
            print("❌ No test user found")
            return False
            
        print(f"1. Testing with user: {recent_user.username}")
        print(f"   📧 Email: {recent_user.email}")
        print(f"   🔓 Active: {recent_user.is_active}")
        print(f"   ✉️  Email verified: {recent_user.is_email_verified}")
        print(f"   🎟️  Verification token: {recent_user.email_verification_token}")
        
        # Test the verification URL
        client = Client()
        verification_url = f'/verify-email/{recent_user.email_verification_token}/'
        print(f"\n2. Testing verification URL: {verification_url}")
        
        response = client.get(verification_url)
        print(f"   Response status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Verification page accessible")
            
            # Check if user is now verified
            recent_user.refresh_from_db()
            print(f"   User active after verification: {recent_user.is_active}")
            print(f"   Email verified after verification: {recent_user.is_email_verified}")
            
        elif response.status_code == 302:
            print("   ✅ Verification successful (redirected)")
            print(f"   📍 Redirected to: {response.url}")
            
            # Check user status after verification
            recent_user.refresh_from_db()
            print(f"   User active after verification: {recent_user.is_active}")
            print(f"   Email verified after verification: {recent_user.is_email_verified}")
        
        # Try to login after verification
        print("\n3. Testing login after email verification...")
        login_data = {
            'username': recent_user.username,
            'password': 'testpassword123'  # Password used in registration
        }
        
        login_response = client.post('/login/', login_data)
        print(f"   Login response status: {login_response.status_code}")
        
        if login_response.status_code == 302:
            print("   ✅ Login successful after verification!")
            print(f"   📍 Redirected to: {login_response.url}")
        else:
            print("   ⚠️  Login still not working")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    print("\n4. Testing invalid token...")
    client = Client()
    invalid_response = client.get('/verify-email/invalid-token-123/')
    print(f"   Invalid token response: {invalid_response.status_code}")
    
    if invalid_response.status_code == 200:
        print("   ✅ Invalid token page accessible (shows error message)")
    
    print("\n" + "=" * 50)
    print("🎉 Email verification test completed!")
    print(f"⏰ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return True

def show_all_test_users():
    """Show all test users for debugging"""
    print("\n👥 All Test Users:")
    print("-" * 30)
    
    test_users = User.objects.filter(username__startswith='testuser').order_by('-date_joined')
    for user in test_users:
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Active: {user.is_active}")
        print(f"Email verified: {user.is_email_verified}")
        print(f"Verification token: {user.email_verification_token}")
        print(f"Date joined: {user.date_joined}")
        print("-" * 30)

if __name__ == "__main__":
    show_all_test_users()
    test_email_verification()
