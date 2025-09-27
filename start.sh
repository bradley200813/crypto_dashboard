#!/bin/bash
# Simple Railway startup script

echo "🚀 Starting Railway deployment..."

# Run database migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# Start the web server
echo "� Starting web server..."
exec gunicorn dashboard.wsgi:application