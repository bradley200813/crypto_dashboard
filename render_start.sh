#!/bin/bash

echo "Starting Render deployment initialization..."

# Set Django settings for production
export DJANGO_SETTINGS_MODULE=dashboard.settings_production

# Run database migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist (optional - only for admin access)
echo "Creating superuser if needed..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
" || echo "Superuser creation skipped"

# Update cryptocurrency data
echo "Updating cryptocurrency data..."
python manage.py update_crypto_data

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Initialization complete. Starting Gunicorn server..."

# Start the application
exec gunicorn dashboard.wsgi:application --bind 0.0.0.0:$PORT