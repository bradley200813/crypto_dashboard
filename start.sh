#!/bin/bash
# Railway startup script to ensure database is properly initialized

echo "🚀 Starting Railway deployment..."

# Run database migrations
echo "📊 Running database migrations..."
python manage.py migrate --noinput

# Check if we have any coins in the database
echo "🔍 Checking for cryptocurrency data..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dashboard.settings')
django.setup()
from market.models import Coin
coin_count = Coin.objects.count()
print(f'Found {coin_count} coins in database')
if coin_count == 0:
    print('📈 Initializing cryptocurrency data...')
    from django.core.management import call_command
    call_command('update_crypto_data')
    print('✅ Cryptocurrency data initialized!')
else:
    print('✅ Database already has cryptocurrency data')
"

echo "🎊 Database setup complete! Starting web server..."

# Start the web server
exec gunicorn dashboard.wsgi:application