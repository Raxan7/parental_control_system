#!/usr/bin/env python3
"""
Test script to create a test user for login testing
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

from django.contrib.auth import get_user_model
from api.models import CustomUser

def create_test_user():
    """Create a test user with verified email"""
    User = get_user_model()
    
    # Check if test user already exists
    if User.objects.filter(username='testuser').exists():
        print("✅ Test user already exists")
        user = User.objects.get(username='testuser')
    else:
        # Create test user
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com', 
            password='testpass123',
            is_parent=True
        )
        print("✅ Test user created")
    
    # Make sure email is verified
    user.is_email_verified = True
    user.save()
    print(f"✅ User verified: {user.is_email_verified}")
    print(f"✅ Username: {user.username}")
    print("✅ Password: testpass123")
    
    return user

if __name__ == '__main__':
    print("🚀 Creating test user for login...")
    create_test_user()
    print("✅ Done! You can now test login with:")
    print("   Username: testuser")
    print("   Password: testpass123")
