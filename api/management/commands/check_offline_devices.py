from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import timedelta
from api.models import ChildDevice, DeviceOfflineNotification
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check for offline devices and send email notifications to parents'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=2,
            help='Number of days offline before sending notification (default: 2)'
        )
        parser.add_argument(
            '--minutes',
            type=int,
            default=None,
            help='Number of minutes offline before sending notification (for testing only)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send notifications even if already sent recently'
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        minutes_threshold = options['minutes']
        force = options['force']
        
        # Use minutes if specified (for testing), otherwise use days (for production)
        if minutes_threshold is not None:
            self.stdout.write(f"Using minutes threshold: {minutes_threshold} minutes (TESTING MODE)")
            cutoff_time = timezone.now() - timedelta(minutes=minutes_threshold)
            time_unit = "minutes"
            time_value = minutes_threshold
        else:
            self.stdout.write(f"Using days threshold: {days_threshold} days (PRODUCTION MODE)")
            cutoff_time = timezone.now() - timedelta(days=days_threshold)
            time_unit = "days"
            time_value = days_threshold
        
        self.stdout.write(f"Checking for devices offline for more than {time_value} {time_unit}...")
        self.stdout.write(f"Cutoff time: {cutoff_time}")
        
        # Find devices that haven't synced in the specified time
        offline_devices = ChildDevice.objects.filter(
            last_sync__lt=cutoff_time
        ).exclude(
            last_sync__isnull=True  # Exclude devices that have never synced
        )
        
        self.stdout.write(f"Found {offline_devices.count()} potentially offline devices")
        
        if not offline_devices.exists():
            self.stdout.write(
                self.style.SUCCESS(f"No devices found offline for more than {time_value} {time_unit}.")
            )
            return
        
        notifications_sent = 0
        
        for device in offline_devices:
            # Calculate time offline
            time_diff = timezone.now() - device.last_sync
            
            if time_unit == "days":
                time_offline = time_diff.days
                time_offline_display = f"{time_offline} days"
            else:
                time_offline = int(time_diff.total_seconds() / 60)  # Convert to minutes
                time_offline_display = f"{time_offline} minutes"
            
            self.stdout.write(f"Device {device} last synced: {device.last_sync} ({time_offline_display} ago)")
            
            # Check if we've already sent a notification for this device recently
            if not force:
                # For production (days), avoid duplicate notifications within 24 hours
                # For testing (minutes), avoid duplicate notifications within 5 minutes
                if time_unit == "days":
                    recent_threshold = timedelta(days=1)
                else:
                    recent_threshold = timedelta(minutes=5)
                    
                recent_notification = DeviceOfflineNotification.objects.filter(
                    device=device,
                    notification_sent_at__gte=timezone.now() - recent_threshold
                ).exists()
                
                if recent_notification:
                    self.stdout.write(
                        f"Skipping {device} - notification already sent recently"
                    )
                    continue
            
            # Send notification email
            success = self.send_offline_notification(device, time_offline, time_unit)
            
            if success:
                # Record that we sent the notification
                DeviceOfflineNotification.objects.create(
                    device=device,
                    days_offline=time_offline if time_unit == "days" else 0,  # Keep days_offline for backward compatibility
                    email_sent_to=device.parent.email
                )
                notifications_sent += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Sent notification for {device} ({time_offline_display} offline)"
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f"Failed to send notification for {device}"
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Process completed. {notifications_sent} notifications sent."
            )
        )

    def send_offline_notification(self, device, time_offline, time_unit):
        """Send offline notification email to the parent"""
        try:
            parent = device.parent
            
            # Format the offline duration display
            if time_unit == "days":
                time_offline_display = f"{time_offline} days"
                subject_time = f"{time_offline} days"
            else:
                time_offline_display = f"{time_offline} minutes"
                subject_time = f"{time_offline} minutes"
            
            # Prepare email context
            context = {
                'parent_name': parent.first_name or parent.username,
                'device_name': device.nickname or device.device_id,
                'device_id': device.device_id,
                'days_offline': time_offline,  # Keep for template compatibility
                'time_offline_display': time_offline_display,
                'last_sync_date': device.last_sync.strftime('%B %d, %Y at %I:%M %p') if device.last_sync else 'Never',
                'is_test': False,
            }
            
            # Render email templates
            subject = f"Device Offline Alert - {context['device_name']} has been offline for {subject_time}"
            text_content = render_to_string(
                'parent_ui/emails/device_offline_notification.txt', 
                context
            )
            html_content = render_to_string(
                'parent_ui/emails/device_offline_notification.html', 
                context
            )
            
            # Send email
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[parent.email],
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Offline notification sent for device {device.device_id} to {parent.email} ({time_offline_display} offline)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send offline notification for device {device.device_id}: {str(e)}")
            return False
