"""
Cryptocurrency Data Service

Fetches real-time cryptocurrency data from CoinGecko API
Updates price information, market data, and price history
"""

import requests
import logging
import json
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import Coin

logger = logging.getLogger(__name__)

class CryptoDataService:
    """Service for fetching real-time cryptocurrency data"""
    
    def __init__(self):
        self.base_url = 'https://api.coingecko.com/api/v3'
        self.timeout = 10
        
    def get_coingecko_ids(self):
        """Map our coin symbols to CoinGecko IDs"""
        # Common cryptocurrency mappings
        symbol_to_id = {
            'BTC': 'bitcoin',
            'ETH': 'ethereum', 
            'ADA': 'cardano',
            'DOT': 'polkadot',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'LTC': 'litecoin',
            'XRP': 'ripple',
            'BCH': 'bitcoin-cash',
            'BNB': 'binancecoin',
            'SOL': 'solana',
            'AVAX': 'avalanche-2',
            'MATIC': 'matic-network',
            'ATOM': 'cosmos',
            'ALGO': 'algorand',
            'VET': 'vechain',
            'ICP': 'internet-computer',
            'FIL': 'filecoin',
            'TRX': 'tron',
            'XLM': 'stellar',
            'ETC': 'ethereum-classic',
            'THETA': 'theta-token',
            'XMR': 'monero',
            'AAVE': 'aave',
            'MKR': 'maker',
            'COMP': 'compound-governance-token',
            'SNX': 'havven',
            'CRV': 'curve-dao-token',
            'YFI': 'yearn-finance',
            'SUSHI': 'sushi',
            'BAT': 'basic-attention-token',
            'ZEC': 'zcash',
            'DASH': 'dash',
            'DCR': 'decred',
            'DOGE': 'dogecoin',
            'SHIB': 'shiba-inu'
        }
        return symbol_to_id
    
    def fetch_price_data(self, symbols=None):
        """
        Fetch current price data for specified cryptocurrencies
        
        Args:
            symbols: List of symbols to update, if None updates all coins in database
            
        Returns:
            dict: Success status and updated coin count
        """
        try:
            if symbols is None:
                # Get all coins from database
                coins = Coin.objects.all()
                symbols = [coin.symbol for coin in coins]
            
            # Map symbols to CoinGecko IDs
            coingecko_ids = self.get_coingecko_ids()
            ids_to_fetch = []
            
            for symbol in symbols:
                if symbol.upper() in coingecko_ids:
                    ids_to_fetch.append(coingecko_ids[symbol.upper()])
            
            if not ids_to_fetch:
                logger.warning("No valid CoinGecko IDs found for provided symbols")
                return {'success': False, 'message': 'No valid symbols found'}
            
            # Fetch data from CoinGecko
            ids_string = ','.join(ids_to_fetch)
            url = f"{self.base_url}/coins/markets"
            
            params = {
                'ids': ids_string,
                'vs_currency': 'usd',
                'order': 'market_cap_desc',
                'per_page': 100,
                'page': 1,
                'sparkline': True,  # Get 7-day price history
                'price_change_percentage': '24h'
            }
            
            logger.info(f"Fetching price data for {len(ids_to_fetch)} cryptocurrencies")
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                updated_count = self.update_coin_data(data)
                
                # Cache the update timestamp
                cache.set('crypto_data_last_update', timezone.now(), 3600)
                
                return {
                    'success': True, 
                    'updated_count': updated_count,
                    'message': f'Successfully updated {updated_count} cryptocurrencies'
                }
            else:
                logger.error(f"CoinGecko API error: {response.status_code}")
                return {'success': False, 'message': f'API error: {response.status_code}'}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching crypto data: {e}")
            return {'success': False, 'message': 'Network error'}
        except Exception as e:
            logger.error(f"Error fetching crypto data: {e}")
            return {'success': False, 'message': str(e)}
    
    def update_coin_data(self, api_data):
        """
        Update coin data in database with API response
        
        Args:
            api_data: List of coin data from CoinGecko API
            
        Returns:
            int: Number of coins updated
        """
        updated_count = 0
        coingecko_ids = self.get_coingecko_ids()
        
        # Reverse mapping (id -> symbol)
        id_to_symbol = {v: k for k, v in coingecko_ids.items()}
        
        for coin_data in api_data:
            try:
                coingecko_id = coin_data.get('id')
                symbol = id_to_symbol.get(coingecko_id)
                
                if not symbol:
                    continue
                
                # Find the coin in our database
                try:
                    coin = Coin.objects.get(symbol=symbol)
                except Coin.DoesNotExist:
                    logger.warning(f"Coin with symbol {symbol} not found in database")
                    continue
                
                # Update price and market data
                coin.current_price = coin_data.get('current_price', coin.current_price)
                coin.market_cap = coin_data.get('market_cap', coin.market_cap)
                coin.volume_24h = coin_data.get('total_volume', coin.volume_24h)
                coin.price_change_24h = coin_data.get('price_change_percentage_24h', coin.price_change_24h)
                
                # Update price history from sparkline data
                sparkline = coin_data.get('sparkline_in_7d', {})
                if sparkline and sparkline.get('price'):
                    # Take last 7 days of price data
                    price_history = sparkline['price'][-7:]
                    coin.price_history = [round(price, 6) for price in price_history if price is not None]
                
                # Update fear and greed index (you could fetch this from another API)
                # For now, calculate a simple momentum indicator
                if coin.price_change_24h > 5:
                    coin.fear_greed = min(80, coin.fear_greed + 5)  # Greed
                elif coin.price_change_24h < -5:
                    coin.fear_greed = max(20, coin.fear_greed - 5)  # Fear
                
                # Update BTC dominance (approximate based on market cap for Bitcoin)
                if symbol == 'BTC':
                    # This is a simplified calculation
                    total_crypto_market = sum(item.get('market_cap', 0) for item in api_data)
                    if total_crypto_market > 0:
                        coin.btc_dominance = (coin.market_cap / total_crypto_market) * 100
                
                coin.save()
                updated_count += 1
                
                logger.debug(f"Updated {symbol}: ${coin.current_price} ({coin.price_change_24h:+.2f}%)")
                
            except Exception as e:
                logger.error(f"Error updating coin {coin_data.get('symbol', 'unknown')}: {e}")
                continue
        
        logger.info(f"Successfully updated {updated_count} coins")
        return updated_count
    
    def get_fear_and_greed_index(self):
        """
        Fetch Fear and Greed Index from alternative API
        
        Returns:
            dict: Fear and Greed index data
        """
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    latest = data['data'][0]
                    return {
                        'value': int(latest.get('value', 50)),
                        'classification': latest.get('value_classification', 'Neutral'),
                        'timestamp': latest.get('timestamp'),
                        'success': True
                    }
            
            return {'success': False, 'message': 'Failed to fetch Fear and Greed Index'}
            
        except Exception as e:
            logger.error(f"Error fetching Fear and Greed Index: {e}")
            return {'success': False, 'message': str(e)}
    
    def get_last_update_time(self):
        """Get the timestamp of the last data update"""
        return cache.get('crypto_data_last_update')
    
    def is_data_fresh(self, max_age_minutes=15):
        """
        Check if data is considered fresh (updated recently)
        
        Args:
            max_age_minutes: Maximum age in minutes for data to be considered fresh
            
        Returns:
            bool: True if data is fresh, False otherwise
        """
        last_update = self.get_last_update_time()
        if not last_update:
            return False
        
        time_diff = timezone.now() - last_update
        return time_diff.total_seconds() < (max_age_minutes * 60)


# Global instance
crypto_data_service = CryptoDataService()