# Offline Device Monitoring Setup Guide

## Overview
This guide explains how to set up automatic monitoring for offline devices in the Parental Control System.

## Components

### 1. Management Command
- **File**: `api/management/commands/check_offline_devices.py`
- **Purpose**: Identifies devices that have been offline for more than N days and sends email notifications
- **Usage**: `python manage.py check_offline_devices --days=2`

### 2. Email Templates
- **HTML Template**: `parent_ui/templates/parent_ui/emails/device_offline_notification.html`
- **Text Template**: `parent_ui/templates/parent_ui/emails/device_offline_notification.txt`
- **Purpose**: Professional email templates for offline device notifications

### 3. Test Email Functionality
- **URL**: `/parent/test-offline-notification/`
- **Purpose**: Allows parents to preview offline notification emails
- **Location**: Dashboard -> Email Notifications section

### 4. Database Model
- **Model**: `DeviceOfflineNotification` in `api/models.py`
- **Purpose**: Tracks when notifications have been sent to prevent spam

## Setup Instructions

### 1. Apply Database Migrations
```bash
cd /path/to/parental_control_system
python manage.py makemigrations
python manage.py migrate
```

### 2. Configure Email Settings
Ensure your Django settings include proper email configuration:

```python
# settings.py
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@domain.com'
EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'Parental Control System <your-email@domain.com>'
```

### 3. Test the System
1. Log into the parent dashboard
2. Go to the "Email Notifications" section
3. Click "Send Test Email" to verify email delivery

### 4. Set Up Automatic Monitoring

#### Option A: Using Cron (Linux/Mac)
```bash
# Edit crontab
crontab -e

# Add this line to check for offline devices daily at 9 AM
0 9 * * * /home/saidi/Projects/FINAL_PROJECT/NEW_FOLDER/FYP/parental_control_system/run_offline_check.sh

# Or check twice daily (9 AM and 9 PM)
0 9,21 * * * /home/saidi/Projects/FINAL_PROJECT/NEW_FOLDER/FYP/parental_control_system/run_offline_check.sh
```

#### Option B: Manual Testing
```bash
cd /path/to/parental_control_system
python manage.py check_offline_devices --days=2
```

#### Option C: Force Check (ignores previous notifications)
```bash
python manage.py check_offline_devices --days=2 --force
```

### 5. Monitor Logs
Check the Django logs and system logs for any issues:
```bash
# Check Django logs
tail -f debug.log

# Check cron logs (if using cron)
tail -f /var/log/parental_control_offline_check.log
```

## Configuration Options

### Management Command Options
- `--days=N`: Check for devices offline for N days (default: 2)
- `--force`: Send notifications even if already sent recently
- `--verbose`: Display detailed output

### Customization
- **Email frequency**: Modify the cron schedule
- **Offline threshold**: Change the `--days` parameter
- **Email templates**: Edit the HTML/text templates
- **Notification logic**: Modify the management command

## Troubleshooting

### Common Issues
1. **Emails not sending**: Check Django email configuration
2. **No devices found**: Ensure devices have synced at least once
3. **Duplicate notifications**: Check DeviceOfflineNotification model
4. **Cron not running**: Verify cron service and script permissions

### Debug Commands
```bash
# Test email settings
python manage.py shell
>>> from django.core.mail import send_mail
>>> send_mail('Test', 'Test message', 'from@example.com', ['to@example.com'])

# Check offline devices without sending emails
python manage.py check_offline_devices --days=2 --dry-run

# View recent notifications
python manage.py shell
>>> from api.models import DeviceOfflineNotification
>>> DeviceOfflineNotification.objects.all()
```

## Security Considerations
- Store email credentials securely (use environment variables)
- Limit email frequency to prevent spam
- Monitor for abuse of the test email feature
- Keep logs secure and rotate them regularly
