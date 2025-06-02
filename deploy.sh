#!/bin/bash

# Deployment script for Render.com
echo "Starting deployment preparation..."

# Set environment variables for production
export DEBUG=False
export DJANGO_SETTINGS_MODULE=parental_control_system.settings

# Navigate to project directory
cd /home/saidi/Projects/FYP/FYP/parental_control_system

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist (optional)
echo "Creating superuser (if needed)..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
" || echo "Superuser creation skipped"

echo "Deployment preparation complete!"
echo "You can now start the server with: gunicorn parental_control_system.wsgi:application"
