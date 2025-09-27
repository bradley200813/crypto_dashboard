#!/bin/bash
set -e  # Exit on any error

echo "🚀 Railway Deployment Starting..."

# Run database migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput || {
    echo "❌ Migration failed, attempting to create database..."
    python manage.py makemigrations --noinput
    python manage.py migrate --noinput
}

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear || {
    echo "⚠️ Static file collection failed, continuing..."
}

# Create staticfiles directory if it doesn't exist
mkdir -p staticfiles

echo "✅ Setup complete! Starting web server..."

# Start the web server
exec gunicorn dashboard.wsgi:application --bind 0.0.0.0:$PORT --workers 2# Simple Railway startup script

echo "🚀 Starting Railway deployment..."

# Run database migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# Start the web server
echo "� Starting web server..."
exec gunicorn dashboard.wsgi:application