#!/bin/bash

# Script to run the offline device check management command
# This script should be added to crontab to run automatically

# Change to the project directory
cd /home/saidi/Projects/FINAL_PROJECT/NEW_FOLDER/FYP/parental_control_system

# Activate virtual environment if you're using one
# source /path/to/your/venv/bin/activate

# Run the management command with 2-day threshold for production
# Use --minutes=1 for testing purposes only
python manage.py check_offline_devices --days=2

# Log the execution
echo "$(date): Offline device check completed (2 days threshold)" >> /var/log/parental_control_offline_check.log
