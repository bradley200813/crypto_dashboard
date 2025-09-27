"""
Management command to update cryptocurrency data

Usage:
    python manage.py update_crypto_data
    python manage.py update_crypto_data --symbols BTC ETH ADA
    python manage.py update_crypto_data --force
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from market.crypto_data_service import crypto_data_service
from market.models import Coin


class Command(BaseCommand):
    help = 'Update cryptocurrency price data from CoinGecko API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific symbols to update (e.g., BTC ETH ADA)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if data is fresh',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO('Starting cryptocurrency data update...'))
        
        # Check if update is needed (unless forced)
        if not options['force'] and crypto_data_service.is_data_fresh(max_age_minutes=15):
            last_update = crypto_data_service.get_last_update_time()
            self.stdout.write(
                self.style.WARNING(
                    f'Data is fresh (last updated: {last_update}). '
                    f'Use --force to update anyway.'
                )
            )
            return
        
        # Get symbols to update
        symbols = options.get('symbols')
        if symbols:
            self.stdout.write(f'Updating specific symbols: {", ".join(symbols)}')
        else:
            coin_count = Coin.objects.count()
            self.stdout.write(f'Updating all {coin_count} cryptocurrencies in database')
        
        # Perform the update
        try:
            result = crypto_data_service.fetch_price_data(symbols)
            
            if result['success']:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Successfully updated {result["updated_count"]} cryptocurrencies'
                    )
                )
                
                # Show some sample updates
                if not symbols:
                    # Show top 5 coins by market cap
                    top_coins = Coin.objects.order_by('-market_cap')[:5]
                    self.stdout.write('\n📊 Top 5 Cryptocurrencies:')
                    for coin in top_coins:
                        change_color = self.style.SUCCESS if coin.price_change_24h >= 0 else self.style.ERROR
                        self.stdout.write(
                            f'   {coin.symbol}: ${coin.current_price:,.2f} '
                            f'({change_color(f"{coin.price_change_24h:+.2f}%")})'
                        )
                
                # Update Fear and Greed Index
                self.stdout.write('\n🎭 Updating Fear and Greed Index...')
                fng_result = crypto_data_service.get_fear_and_greed_index()
                if fng_result['success']:
                    self.stdout.write(
                        f'   Current index: {fng_result["value"]} ({fng_result["classification"]})'
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'   ⚠️ {fng_result["message"]}')
                    )
                
            else:
                self.stdout.write(
                    self.style.ERROR(f'❌ Update failed: {result["message"]}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Unexpected error: {str(e)}')
            )
        
        self.stdout.write(f'\n🕒 Update completed at {timezone.now()}')