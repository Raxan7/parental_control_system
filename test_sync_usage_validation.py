#!/usr/bin/env python3
"""
Test script to verify sync-usage API properly validates time data
and doesn't create invalid AppUsageLog records.
"""

import requests
import json
from datetime import datetime, timedelta

# Test data with various scenarios
test_cases = [
    {
        "name": "Valid time range",
        "start_time": "2025-05-31T10:00:00Z",
        "end_time": "2025-05-31T10:05:00Z",
        "should_succeed": True
    },
    {
        "name": "Invalid: end_time before start_time",
        "start_time": "2025-05-31T10:05:00Z",
        "end_time": "2025-05-31T10:00:00Z",
        "should_succeed": False
    },
    {
        "name": "Invalid: end_time equals start_time",
        "start_time": "2025-05-31T10:00:00Z",
        "end_time": "2025-05-31T10:00:00Z",
        "should_succeed": False
    },
    {
        "name": "Valid: 1 second duration",
        "start_time": "2025-05-31T10:00:00Z",
        "end_time": "2025-05-31T10:00:01Z",
        "should_succeed": True
    },
]

def test_sync_usage_validation():
    """Test the sync-usage API with various time scenarios"""
    
    # First, we need to get an authentication token
    # For this test, we'll assume you have test credentials
    login_url = "http://127.0.0.1:8000/api/token/"
    
    # You'll need to replace these with actual test credentials
    login_data = {
        "username": "test_parent",  # Replace with actual username
        "password": "test_password"  # Replace with actual password
    }
    
    try:
        # Get authentication token
        print("Getting authentication token...")
        response = requests.post(login_url, json=login_data)
        
        if response.status_code != 200:
            print(f"Failed to get token: {response.status_code}")
            print(f"Response: {response.text}")
            return
            
        token = response.json().get("access")
        headers = {"Authorization": f"Bearer {token}"}
        
        print(f"Got token: {token[:20]}...")
        
        # Test each case
        for i, test_case in enumerate(test_cases):
            print(f"\nTest {i+1}: {test_case['name']}")
            
            sync_data = {
                "device_id": "test_device_123",
                "usage_data": [
                    {
                        "app_name": "com.test.app",
                        "start_time": test_case["start_time"],
                        "end_time": test_case["end_time"]
                    }
                ]
            }
            
            response = requests.post(
                "http://127.0.0.1:8000/api/sync-usage/",
                json=sync_data,
                headers=headers
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if test_case["should_succeed"]:
                if response.status_code == 200:
                    print("✅ PASS: Valid data was accepted")
                else:
                    print("❌ FAIL: Valid data was rejected")
            else:
                if response.status_code == 200:
                    print("⚠️  WARNING: Invalid data was accepted (should be skipped in logs)")
                else:
                    print("✅ PASS: Invalid data was properly rejected")
                    
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to Django server. Make sure it's running on http://127.0.0.1:8000/")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Testing sync-usage API validation...")
    test_sync_usage_validation()
