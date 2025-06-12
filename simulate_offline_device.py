#!/usr/bin/env python
"""
Script to simulate an offline device for testing offline notifications.
This script will set a device's last_sync time to 2 minutes ago.
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
from api.models import ChildDevice, CustomUser


def simulate_offline_device():
    """Make a device appear offline by setting its last_sync to 2 minutes ago"""
    try:
        # Find a device to make offline
        device = ChildDevice.objects.first()
        
        if not device:
            print("❌ No devices found in database")
            print("💡 You need to have at least one device registered to test offline notifications")
            return False
        
        # Set last_sync to 2 minutes ago (more than the 1-minute threshold)
        old_last_sync = device.last_sync
        device.last_sync = timezone.now() - timedelta(minutes=2)
        device.save()
        
        print(f"✅ Device {device.nickname or device.device_id} simulated as offline")
        print(f"📅 Previous last_sync: {old_last_sync}")
        print(f"📅 New last_sync: {device.last_sync}")
        print(f"👤 Parent email: {device.parent.email}")
        print(f"⏰ Device is now 2 minutes offline (threshold is 1 minute)")
        print("\n🔄 You can now run: python manage.py check_offline_devices --minutes=1")
        
        return True
        
    except Exception as e:
        print(f"❌ Error simulating offline device: {str(e)}")
        return False


def reset_device_online():
    """Reset all devices to be online (current time sync)"""
    try:
        devices = ChildDevice.objects.all()
        
        if not devices.exists():
            print("❌ No devices found in database")
            return False
        
        updated_count = 0
        for device in devices:
            device.last_sync = timezone.now()
            device.save()
            updated_count += 1
            print(f"✅ Device {device.nickname or device.device_id} set as online")
        
        print(f"\n🔄 {updated_count} devices reset to online status")
        return True
        
    except Exception as e:
        print(f"❌ Error resetting devices: {str(e)}")
        return False


def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        print("🔄 Resetting all devices to online status...")
        reset_device_online()
    else:
        print("🎯 Simulating offline device for testing...")
        simulate_offline_device()
        print("\n📧 To test automatic email notification:")
        print("   python manage.py check_offline_devices --minutes=1")
        print("\n🔄 To reset devices back online:")
        print("   python simulate_offline_device.py --reset")


if __name__ == "__main__":
    main()
