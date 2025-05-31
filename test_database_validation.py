#!/usr/bin/env python3
"""
Simple test to validate our sync-usage API fixes by checking database records
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parental_control_system.settings')
django.setup()

from api.models import AppUsageLog
from datetime import datetime

def test_database_validation():
    """Test that our database constraint is working"""
    
    print("Testing database constraint validation...")
    
    # Check current count of records
    initial_count = AppUsageLog.objects.count()
    print(f"Initial AppUsageLog count: {initial_count}")
    
    # Try to create an invalid record directly (this should fail)
    try:
        invalid_log = AppUsageLog(
            device_id=1,  # Assuming device exists
            app_name="test.app",
            start_time=datetime(2025, 5, 31, 10, 5, 0),
            end_time=datetime(2025, 5, 31, 10, 0, 0),  # end before start
        )
        invalid_log.save()
        print("❌ FAIL: Invalid record was saved (this should not happen)")
    except Exception as e:
        print(f"✅ PASS: Database constraint prevented invalid record: {e}")
    
    # Try to create a valid record
    try:
        from api.models import ChildDevice
        device = ChildDevice.objects.first()
        if device:
            valid_log = AppUsageLog(
                device=device,
                app_name="test.app",
                start_time=datetime(2025, 5, 31, 10, 0, 0),
                end_time=datetime(2025, 5, 31, 10, 5, 0),  # end after start
            )
            valid_log.save()
            print(f"✅ PASS: Valid record was saved with duration: {valid_log.duration}")
            
            # Clean up test record
            valid_log.delete()
        else:
            print("⚠️  No devices found to test with")
            
    except Exception as e:
        print(f"❌ FAIL: Valid record could not be saved: {e}")
    
    # Check that count is back to initial
    final_count = AppUsageLog.objects.count()
    print(f"Final AppUsageLog count: {final_count}")
    
    if final_count == initial_count:
        print("✅ PASS: Database state is clean after test")
    else:
        print("⚠️  WARNING: Database state changed during test")

if __name__ == "__main__":
    test_database_validation()
