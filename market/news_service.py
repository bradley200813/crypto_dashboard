import requests
import logging
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class CryptoNewsService:
    """Service class for fetching cryptocurrency news from various APIs"""
    
    def __init__(self):
        self.news_api_key = getattr(settings, 'NEWS_API_KEY', 'demo_key')
        self.base_url = getattr(settings, 'NEWS_API_BASE_URL', 'https://newsapi.org/v2/')
        
    def get_crypto_news(self, category='all', page=1, page_size=20):
        """
        Fetch cryptocurrency news articles
        
        Args:
            category: 'all', 'bitcoin', 'ethereum', 'defi'
            page: Page number for pagination
            page_size: Number of articles per page (max 100 for NewsAPI)
            
        Returns:
            dict: Contains articles, total_results, and metadata
        """
        # Limit page_size to NewsAPI maximum
        page_size = min(page_size, 100)
        
        # Create cache key
        cache_key = f"crypto_news_{category}_{page}_{page_size}"
        
        # Try to get from cache first
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"Returning cached news data for {category}, page {page}")
            return cached_data
        
        try:
            # Map categories to search queries
            queries = {
                'all': 'cryptocurrency OR bitcoin OR ethereum OR crypto OR blockchain OR "digital currency" OR DeFi',
                'bitcoin': 'bitcoin OR BTC OR "bitcoin price" OR "bitcoin news"',
                'ethereum': 'ethereum OR ETH OR "smart contracts" OR "ethereum price"',
                'defi': 'DeFi OR "decentralized finance" OR "yield farming" OR DEX OR "liquidity mining"'
            }
            
            query = queries.get(category, queries['all'])
            
            # NewsAPI endpoint for everything
            url = f"{self.base_url}everything"
            
            params = {
                'q': query,
                'sortBy': 'publishedAt',
                'language': 'en',
                'page': page,
                'pageSize': page_size,
                'apiKey': self.news_api_key
            }
            
            # Add date filter for recent articles (last 30 days for more content)
            from_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            params['from'] = from_date
            
            logger.info(f"Fetching news for category: {category}, page: {page}")
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'ok':
                    # Process articles
                    processed_articles = self._process_articles(data.get('articles', []), category)
                    
                    result = {
                        'articles': processed_articles,
                        'total_results': data.get('totalResults', 0),
                        'status': 'success',
                        'category': category,
                        'page': page,
                        'page_size': page_size,
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    # Cache the results for 30 minutes
                    cache.set(cache_key, result, 1800)
                    
                    logger.info(f"Successfully fetched {len(processed_articles)} articles for {category}, page {page}")
                    return result
                else:
                    logger.error(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                    return {
                        'articles': [],
                        'total_results': 0,
                        'status': 'api_error',
                        'category': category,
                        'page': page,
                        'page_size': page_size,
                        'error_message': data.get('message', 'Unknown API error'),
                        'last_updated': datetime.now().isoformat()
                    }
                    
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return {
                    'articles': [],
                    'total_results': 0,
                    'status': 'http_error',
                    'category': category,
                    'page': page,
                    'page_size': page_size,
                    'error_message': f'HTTP {response.status_code} error',
                    'last_updated': datetime.now().isoformat()
                }
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return {
                'articles': [],
                'total_results': 0,
                'status': 'request_error',
                'category': category,
                'page': page,
                'page_size': page_size,
                'error_message': f'Network error: {str(e)}',
                'last_updated': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                'articles': [],
                'total_results': 0,
                'status': 'unexpected_error',
                'category': category,
                'page': page,
                'page_size': page_size,
                'error_message': f'Unexpected error: {str(e)}',
                'last_updated': datetime.now().isoformat()
            }
    
    def _process_articles(self, articles, category):
        """Process and clean article data"""
        processed = []
        
        for article in articles:
            # Skip articles with missing essential data
            if not article.get('title') or not article.get('url'):
                continue
                
            # Skip articles that are likely not crypto-related if they don't contain keywords
            title = (article.get('title') or '').lower()
            description = (article.get('description') or '').lower()
            crypto_keywords = ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'defi', 'nft', 'trading']
            
            if not any(keyword in title or keyword in description for keyword in crypto_keywords):
                continue
            
            # Format the article
            try:
                processed_article = {
                    'id': abs(hash(article.get('url', ''))),  # Generate ID from URL
                    'title': article.get('title') or 'No Title',
                    'description': article.get('description') or 'No description available',
                    'url': article.get('url'),
                    'source': article.get('source', {}).get('name', 'Unknown') if article.get('source') else 'Unknown',
                    'published_at': self._format_date(article.get('publishedAt')),
                    'image': article.get('urlToImage'),
                    'category': self._determine_category(article, category),
                    'author': article.get('author')
                }
                
                processed.append(processed_article)
            except Exception as e:
                logger.error(f"Error processing article: {str(e)}")
                continue  # Skip this article and continue with others
            
        return processed
    
    def _determine_category(self, article, requested_category):
        """Determine article category based on content"""
        if requested_category != 'all':
            return requested_category.title()
            
        title = (article.get('title') or '').lower()
        description = (article.get('description') or '').lower()
        content = f"{title} {description}"
        
        if 'bitcoin' in content or 'btc' in content:
            return 'Bitcoin'
        elif 'ethereum' in content or 'eth' in content:
            return 'Ethereum'  
        elif 'defi' in content or 'decentralized finance' in content:
            return 'DeFi'
        elif 'nft' in content:
            return 'NFT'
        elif 'trading' in content or 'exchange' in content:
            return 'Trading'
        else:
            return 'Crypto'
    
    def _format_date(self, date_string):
        """Format date string to relative time"""
        if not date_string:
            return 'Unknown'
            
        try:
            # Parse the ISO date string
            article_date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            now = datetime.now(article_date.tzinfo)
            
            diff = now - article_date
            
            if diff.days > 0:
                return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
            elif diff.seconds > 3600:
                hours = diff.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif diff.seconds > 60:
                minutes = diff.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
                
        except Exception as e:
            logger.error(f"Date formatting error: {str(e)}")
            return 'Recently'

# Global instance
crypto_news_service = CryptoNewsService()