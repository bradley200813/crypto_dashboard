from django.shortcuts import render
from .models import Coin, Watchlist, Portfolio, Transaction
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.db import models
from django.views.decorators.http import require_http_methods
from django_ratelimit.decorators import ratelimit
from decimal import Decimal
import json
from .crypto_data_service import crypto_data_service






def add_to_watchlist(request):
    """Add a coin to user's watchlist"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            symbol = data.get('symbol', '').upper()
            
            coin = Coin.objects.get(symbol=symbol)
            
            if request.user.is_authenticated:
                # Check if already in watchlist
                if Watchlist.objects.filter(user=request.user, coin=coin).exists():
                    return JsonResponse({"error": "Coin already in watchlist"}, status=400)
                
                # Add to watchlist
                Watchlist.objects.create(user=request.user, coin=coin)
            else:
                # For anonymous users, use session
                session_watchlist = request.session.get('watchlist', [])
                if symbol in session_watchlist:
                    return JsonResponse({"error": "Coin already in watchlist"}, status=400)
                
                session_watchlist.append(symbol)
                request.session['watchlist'] = session_watchlist
            
            return JsonResponse({"success": True, "message": f"{coin.name} added to watchlist"})
            
        except Coin.DoesNotExist:
            return JsonResponse({"error": "Coin not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


def dashboard(request):
    # Get user watchlist
    if request.user.is_authenticated:
        user_watchlist = Watchlist.objects.filter(user=request.user).select_related('coin')
    else:
        # For anonymous users, get watchlist from session
        session_watchlist = request.session.get('watchlist', [])
        # Ensure consistent case handling (session should have uppercase symbols)
        session_watchlist_upper = [symbol.upper() for symbol in session_watchlist]
        coins = Coin.objects.filter(symbol__in=session_watchlist_upper)
        # Create mock Watchlist objects for template consistency
        from collections import namedtuple
        MockWatchlistItem = namedtuple('MockWatchlistItem', ['coin'])
        user_watchlist = [MockWatchlistItem(coin=coin) for coin in coins]
    
    try:
        top_coins = Coin.objects.all().order_by('-market_cap')[:10]
        
        # Default to first coin in watchlist if available, otherwise first coin in database
        if user_watchlist:
            if request.user.is_authenticated:
                default_coin = user_watchlist[0].coin
            else:
                # For anonymous users, user_watchlist is a list of MockWatchlistItem objects
                default_coin = user_watchlist[0].coin
        else:
            default_coin = Coin.objects.first()  # Get first coin instead of specifically BTC
    except Exception as e:
        # Database tables don't exist yet or are empty
        top_coins = []
        default_coin = None
        user_watchlist = []

    context = {
        "top_coins": top_coins,
        "watchlist": user_watchlist,
        "selected_coin": default_coin,
    }
    return render(request, "market/index.html", context)


#@login_required
def coin_data(request, symbol):
    try:
        coin = Coin.objects.get(symbol=symbol.upper())
        
        # Generate realistic price history if empty
        price_history = coin.price_history
        if not price_history or len(price_history) == 0:
            base_price = float(coin.current_price)
            # Generate 7 days of realistic price variations around current price
            import random
            price_history = [
                round(base_price * (0.92 + random.random() * 0.16), 2)  # Random between 92% and 108% of current price
                for _ in range(7)
            ]
            # Ensure the last value is close to current price
            price_history[-1] = base_price
        
        data = {
            "name": coin.name,
            "symbol": coin.symbol,
            "current_price": float(coin.current_price),
            "market_cap": int(coin.market_cap),
            "volume_24h": int(coin.volume_24h),
            "btc_dominance": float(coin.btc_dominance),
            "fear_greed": int(coin.fear_greed),
            "price_history": price_history
        }
        return JsonResponse(data)
    except Coin.DoesNotExist:
        return JsonResponse({"error": "Coin not found"}, status=404)


def add_to_watchlist(request):
    """Add a coin to user's watchlist"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            symbol = data.get('symbol', '').upper()
            
            coin = Coin.objects.get(symbol=symbol)
            
            # Check if already in watchlist
            if Watchlist.objects.filter(user=request.user, coin=coin).exists():
                return JsonResponse({"error": "Coin already in watchlist"}, status=400)
            
            # Add to watchlist
            Watchlist.objects.create(user=request.user, coin=coin)
            return JsonResponse({"success": True, "message": f"{coin.name} added to watchlist"})
            
        except Coin.DoesNotExist:
            return JsonResponse({"error": "Coin not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


@ratelimit(key='user', rate='60/m', method='POST', block=True)
@login_required
def remove_from_watchlist(request):
    """Remove a coin from user's watchlist"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            symbol = data.get('symbol', '').upper()
            
            coin = Coin.objects.get(symbol=symbol)
            
            if request.user.is_authenticated:
                # Remove from database watchlist
                watchlist_item = Watchlist.objects.filter(user=request.user, coin=coin).first()
                if watchlist_item:
                    watchlist_item.delete()
                    return JsonResponse({"success": True, "message": f"{coin.name} removed from watchlist"})
                else:
                    return JsonResponse({"error": "Coin not in watchlist"}, status=404)
            else:
                # Remove from session watchlist
                session_watchlist = request.session.get('watchlist', [])
                if symbol in session_watchlist:
                    session_watchlist.remove(symbol)
                    request.session['watchlist'] = session_watchlist
                    return JsonResponse({"success": True, "message": f"{coin.name} removed from watchlist"})
                else:
                    return JsonResponse({"error": "Coin not in watchlist"}, status=404)
                
        except Coin.DoesNotExist:
            return JsonResponse({"error": "Coin not found"}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    
    return JsonResponse({"error": "Method not allowed"}, status=405)


def get_watchlist_status(request, symbol):
    """Check if a coin is in user's watchlist"""
    try:
        coin = Coin.objects.get(symbol=symbol.upper())
        
        if request.user.is_authenticated:
            # For authenticated users, check database
            is_in_watchlist = Watchlist.objects.filter(user=request.user, coin=coin).exists()
        else:
            # For anonymous users, check session
            session_watchlist = request.session.get('watchlist', [])
            # Ensure consistent case handling
            session_watchlist_upper = [s.upper() for s in session_watchlist]
            is_in_watchlist = symbol.upper() in session_watchlist_upper
            
        return JsonResponse({"in_watchlist": is_in_watchlist})
        
    except Coin.DoesNotExist:
        return JsonResponse({"error": "Coin not found"}, status=404)


def search_coins(request):
    """Search for coins by name or symbol"""
    query = request.GET.get('q', '').strip()
    limit = int(request.GET.get('limit', 10))  # Default limit of 10
    
    # Get user's current watchlist for star states
    watchlist_symbols = set()
    if request.user.is_authenticated:
        watchlist_symbols = set(Watchlist.objects.filter(user=request.user).values_list('coin__symbol', flat=True))
    else:
        # For anonymous users, check session
        session_watchlist = request.session.get('watchlist', [])
        # Ensure consistent case handling (convert session data to uppercase)
        watchlist_symbols = set(symbol.upper() for symbol in session_watchlist)
    
    if len(query) < 1:
        # Return all coins if no query (for header search)
        coins = Coin.objects.all().order_by('name')[:limit]
    else:
        # Search by name or symbol (case insensitive)
        coins = Coin.objects.filter(
            models.Q(name__icontains=query) | models.Q(symbol__icontains=query)
        ).order_by('name')[:limit]
    
    # For watchlist modal, get user's current watchlist to exclude already added coins
    # For header search, show all coins regardless of watchlist status
    is_watchlist_search = request.GET.get('watchlist_search', 'false').lower() == 'true'
    
    coin_data = []
    for coin in coins:
        # For watchlist modal, exclude coins already in watchlist
        # For header search, show all coins
        if not is_watchlist_search or coin.symbol not in watchlist_symbols:
            coin_data.append({
                'symbol': coin.symbol,
                'name': coin.name,
                'current_price': float(coin.current_price),
                'price_change_24h': float(coin.price_change_24h),
                'in_watchlist': coin.symbol in watchlist_symbols,
            })
    
    return JsonResponse({'coins': coin_data})


def coin_detail(request, symbol):
    """Display detailed information for a specific coin"""
    try:
        coin = Coin.objects.get(symbol=symbol.upper())
        
        # Generate realistic price history if empty
        price_history = coin.price_history
        if not price_history or len(price_history) == 0:
            base_price = float(coin.current_price)
            # Generate 30 days of realistic price variations around current price
            import random
            price_history = [
                round(base_price * (0.85 + random.random() * 0.3), 2)  # Random between 85% and 115% of current price
                for _ in range(30)
            ]
            # Ensure the last value is close to current price
            price_history[-1] = base_price
        
        context = {
            'coin': coin,
        }
        return render(request, 'market/coin_detail.html', context)
        
    except Coin.DoesNotExist:
        # Redirect to dashboard if coin not found
        from django.shortcuts import redirect
        return redirect('market:dashboard')


def get_filtered_coins(request):
    """Get coins filtered by category (all, gainers, losers) with pagination and sorting"""
    filter_type = request.GET.get('filter', 'all')
    limit = int(request.GET.get('limit', 20))  # Increased default limit
    offset = int(request.GET.get('offset', 0))  # For pagination
    sort_by = request.GET.get('sort_by', '')  # Sorting parameter
    sort_order = request.GET.get('sort_order', 'desc')  # asc or desc
    
    # Get user's current watchlist
    watchlist_symbols = set()
    if request.user.is_authenticated:
        watchlist_symbols = set(Watchlist.objects.filter(user=request.user).values_list('coin__symbol', flat=True))
    else:
        # For anonymous users, check session
        session_watchlist = request.session.get('watchlist', [])
        # Ensure consistent case handling (convert session data to uppercase)
        watchlist_symbols = set(symbol.upper() for symbol in session_watchlist)
    
    # Base query
    coins_query = Coin.objects.all()
    
    # Apply filtering
    if filter_type == 'gainers':
        # Order by highest positive price change
        coins_query = coins_query.filter(price_change_24h__gt=0)
        if not sort_by:  # Default sort for gainers
            coins_query = coins_query.order_by('-price_change_24h')
    elif filter_type == 'losers':
        # Order by biggest negative price change (most negative first)
        coins_query = coins_query.filter(price_change_24h__lt=0)
        if not sort_by:  # Default sort for losers
            coins_query = coins_query.order_by('price_change_24h')
    else:
        # All coins
        if not sort_by:  # Default sort for all
            coins_query = coins_query.order_by('-market_cap')
    
    # Apply custom sorting if specified
    if sort_by:
        sort_field = sort_by
        # Map frontend field names to backend field names
        field_mapping = {
            'name': 'name',
            'price': 'current_price',
            'change': 'price_change_24h',
            'market_cap': 'market_cap',
            'volume': 'volume_24h'
        }
        
        if sort_by in field_mapping:
            sort_field = field_mapping[sort_by]
            if sort_order == 'asc':
                coins_query = coins_query.order_by(sort_field)
            else:  # desc
                coins_query = coins_query.order_by(f'-{sort_field}')
    
    # Get total count before applying pagination
    total_count = coins_query.count()
    
    # Apply pagination
    coins = coins_query[offset:offset + limit]
    
    # Check if there are more results
    has_more = (offset + limit) < total_count
    
    # Prepare coin data
    coin_data = []
    for coin in coins:
        coin_data.append({
            'symbol': coin.symbol,
            'name': coin.name,
            'current_price': float(coin.current_price),
            'price_change_24h': float(coin.price_change_24h),
            'market_cap': int(coin.market_cap),
            'volume_24h': int(coin.volume_24h),
            'in_watchlist': coin.symbol in watchlist_symbols,
        })
    
    return JsonResponse({
        'coins': coin_data, 
        'filter': filter_type,
        'has_more': has_more,
        'total_count': total_count,
        'loaded_count': offset + len(coin_data)
    })


def watchlist(request):
    """Display user's watchlist page"""
    if request.user.is_authenticated:
        # For authenticated users, get from database
        watchlist_entries = Watchlist.objects.filter(user=request.user).select_related('coin')
        watchlist_coins = [entry.coin for entry in watchlist_entries]
    else:
        # For anonymous users, get from session
        session_watchlist = request.session.get('watchlist', [])
        # Ensure consistent case handling (convert session data to uppercase)
        session_watchlist_upper = [symbol.upper() for symbol in session_watchlist]
        watchlist_coins = list(Coin.objects.filter(symbol__in=session_watchlist_upper))
    
    # Calculate summary statistics
    if watchlist_coins:
        total_value = sum(coin.current_price for coin in watchlist_coins)
        gainers_count = sum(1 for coin in watchlist_coins if coin.price_change_24h > 0)
        losers_count = sum(1 for coin in watchlist_coins if coin.price_change_24h < 0)
    else:
        total_value = 0
        gainers_count = 0
        losers_count = 0
    
    context = {
        'watchlist_coins': watchlist_coins,
        'total_value': total_value,
        'gainers_count': gainers_count,
        'losers_count': losers_count,
    }
    
    return render(request, 'market/watchlist.html', context)


def watchlist_api(request):
    """API endpoint to get watchlist data"""
    if request.user.is_authenticated:
        # For authenticated users, get from database
        watchlist_entries = Watchlist.objects.filter(user=request.user).select_related('coin')
        watchlist_data = [{
            'coin': {
                'symbol': entry.coin.symbol,
                'name': entry.coin.name,
                'current_price': float(entry.coin.current_price),
                'price_change_24h': float(entry.coin.price_change_24h)
            }
        } for entry in watchlist_entries]
    else:
        # For anonymous users, get from session
        session_watchlist = request.session.get('watchlist', [])
        session_watchlist_upper = [symbol.upper() for symbol in session_watchlist]
        coins = Coin.objects.filter(symbol__in=session_watchlist_upper)
        watchlist_data = [{
            'coin': {
                'symbol': coin.symbol,
                'name': coin.name,
                'current_price': float(coin.current_price),
                'price_change_24h': float(coin.price_change_24h)
            }
        } for coin in coins]
    
    return JsonResponse({'watchlist': watchlist_data})


@require_http_methods(["POST"])
def toggle_watchlist(request):
    """Toggle a coin in/out of watchlist"""
    try:
        data = json.loads(request.body)
        symbol = data.get('symbol')
        
        if not symbol:
            return JsonResponse({'success': False, 'message': 'Symbol is required'})
        
        try:
            coin = Coin.objects.get(symbol=symbol)
        except Coin.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Coin not found'})
        
        if request.user.is_authenticated:
            # For authenticated users, use database
            watchlist_entry, created = Watchlist.objects.get_or_create(
                user=request.user, 
                coin=coin
            )
            
            if created:
                # Added to watchlist
                is_watching = True
                message = f"{coin.symbol} added to watchlist"
            else:
                # Remove from watchlist
                watchlist_entry.delete()
                is_watching = False
                message = f"{coin.symbol} removed from watchlist"
        else:
            # For anonymous users, use session
            watchlist = request.session.get('watchlist', [])
            
            # Ensure consistent case comparison (use uppercase)
            symbol_upper = symbol.upper()
            
            if symbol_upper in watchlist:
                # Remove from watchlist
                watchlist.remove(symbol_upper)
                is_watching = False
                message = f"{coin.symbol} removed from watchlist"
            else:
                # Add to watchlist
                watchlist.append(symbol_upper)
                is_watching = True
                message = f"{coin.symbol} added to watchlist"
            
            request.session['watchlist'] = watchlist
        
        return JsonResponse({
            'success': True, 
            'is_watching': is_watching,
            'message': message
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def news(request):
    """Display crypto news page with real API integration"""
    from .news_service import crypto_news_service
    
    # Get filter parameter
    category = request.GET.get('category', 'all')
    
    # Fetch news from API
    news_data = crypto_news_service.get_crypto_news(category=category, page_size=15)
    
    articles = news_data.get('articles', [])
    status = news_data.get('status', 'success')
    
    # Separate featured articles (first 2 with images) from regular articles
    featured_articles = []
    regular_articles = []
    
    if status == 'success' and articles:
        for article in articles:
            if len(featured_articles) < 2 and article.get('image'):
                featured_articles.append(article)
            else:
                regular_articles.append(article)
        
        # If we don't have enough featured articles with images, use first 2 regardless
        if len(featured_articles) < 2 and len(articles) >= 2:
            featured_articles = articles[:2]
            regular_articles = articles[2:]
    
    from datetime import datetime
    
    context = {
        'featured_articles': featured_articles,
        'articles': regular_articles,
        'last_updated': datetime.now().strftime('%H:%M'),
        'current_category': category,
        'news_status': status,
        'total_results': news_data.get('total_results', 0),
        'error_message': news_data.get('error_message', ''),
        'has_api_key': crypto_news_service.news_api_key != 'demo_key'
    }
    
    return render(request, 'market/news.html', context)


def get_filtered_news(request):
    """API endpoint to get filtered news articles"""
    from .news_service import crypto_news_service
    
    category = request.GET.get('category', 'all')
    page = int(request.GET.get('page', 1))
    
    try:
        news_data = crypto_news_service.get_crypto_news(category=category, page=page)
        
        articles = news_data.get('articles', [])
        
        # Format articles for JSON response
        formatted_articles = []
        for article in articles:
            formatted_articles.append({
                'id': article['id'],
                'title': article['title'],
                'description': article['description'],
                'category': article['category'],
                'source': article['source'],
                'published_at': article['published_at'],
                'url': article['url'],
                'image': article.get('image')
            })
        
        return JsonResponse({
            'success': True,
            'articles': formatted_articles,
            'total_results': news_data.get('total_results', 0),
            'category': category,
            'page': page,
            'status': news_data.get('status', 'success')
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


def portfolio(request):
    """Display user's portfolio page"""
    
    if not request.user.is_authenticated:
        # For anonymous users, show a sign-up encouragement page
        context = {
            'portfolio_data': [],
            'total_value': 0,
            'total_invested': 0,
            'total_gain_loss': 0,
            'overall_performance': 0,
            'recent_transactions': [],
            'has_holdings': False,
            'is_anonymous': True,
        }
        return render(request, 'market/portfolio.html', context)
    
    # Get user's portfolio holdings
    portfolio_entries = Portfolio.objects.filter(user=request.user).select_related('coin').order_by('-total_invested')
    
    # Calculate portfolio summary statistics
    total_value = 0
    total_invested = 0
    total_gain_loss = 0
    
    portfolio_data = []
    for entry in portfolio_entries:
        current_value = entry.current_value
        gain_loss = entry.unrealized_gain_loss
        gain_loss_percentage = entry.unrealized_gain_loss_percentage
        
        total_value += current_value
        total_invested += float(entry.total_invested)
        total_gain_loss += gain_loss
        
        portfolio_data.append({
            'entry': entry,
            'current_value': current_value,
            'gain_loss': gain_loss,
            'gain_loss_percentage': gain_loss_percentage,
        })
    
    # Calculate overall portfolio performance
    overall_performance = 0
    if total_invested > 0:
        overall_performance = (total_gain_loss / total_invested) * 100
    
    # Get recent transactions
    recent_transactions = Transaction.objects.filter(user=request.user).select_related('coin')[:10]
    
    context = {
        'portfolio_data': portfolio_data,
        'total_value': total_value,
        'total_invested': total_invested,
        'total_gain_loss': total_gain_loss,
        'overall_performance': overall_performance,
        'recent_transactions': recent_transactions,
        'has_holdings': len(portfolio_entries) > 0,
    }
    
    return render(request, 'market/portfolio.html', context)


@ratelimit(key='user', rate='30/m', method='POST', block=True)
@require_http_methods(["POST"])
@login_required
def add_transaction(request):
    """Add a buy/sell transaction"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please login to manage your portfolio'})
    
    try:
        data = json.loads(request.body)
        symbol = data.get('symbol', '').upper()
        transaction_type = data.get('transaction_type', 'buy')
        amount = Decimal(str(data.get('amount', 0)))
        price_per_coin = Decimal(str(data.get('price_per_coin', 0)))
        notes = data.get('notes', '')
        
        if not symbol or amount <= 0 or price_per_coin <= 0:
            return JsonResponse({'success': False, 'message': 'Invalid transaction data'})
        
        # Get coin
        try:
            coin = Coin.objects.get(symbol=symbol)
        except Coin.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Coin not found'})
        
        # Check if selling more than owned
        if transaction_type == 'sell':
            portfolio_entry = Portfolio.objects.filter(user=request.user, coin=coin).first()
            if not portfolio_entry or portfolio_entry.total_amount < amount:
                return JsonResponse({
                    'success': False, 
                    'message': f'Insufficient {coin.symbol} balance. You own {portfolio_entry.total_amount if portfolio_entry else 0} coins.'
                })
        
        # Create transaction (this will automatically update portfolio)
        transaction = Transaction.objects.create(
            user=request.user,
            coin=coin,
            transaction_type=transaction_type,
            amount=amount,
            price_per_coin=price_per_coin,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'message': f'{transaction_type.upper()} transaction added successfully',
            'transaction': {
                'id': transaction.id,
                'type': transaction.transaction_type,
                'amount': float(transaction.amount),
                'price': float(transaction.price_per_coin),
                'total_value': float(transaction.total_value),
                'date': transaction.transaction_date.isoformat()
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})
    except ValueError as e:
        return JsonResponse({'success': False, 'message': f'Invalid number format: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_http_methods(["GET"])
def portfolio_analytics(request):
    """Get portfolio analytics data for charts"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'})
    
    try:
        portfolio_entries = Portfolio.objects.filter(user=request.user).select_related('coin')
        
        # Portfolio allocation data (pie chart)
        allocation_data = []
        total_value = sum(entry.current_value for entry in portfolio_entries)
        
        for entry in portfolio_entries:
            if total_value > 0:
                percentage = (entry.current_value / total_value) * 100
                allocation_data.append({
                    'name': entry.coin.name,
                    'symbol': entry.coin.symbol,
                    'value': entry.current_value,
                    'percentage': round(percentage, 2),
                    'amount': float(entry.total_amount)
                })
        
        # Performance data (gains/losses)
        performance_data = []
        for entry in portfolio_entries:
            performance_data.append({
                'name': entry.coin.name,
                'symbol': entry.coin.symbol,
                'invested': float(entry.total_invested),
                'current_value': entry.current_value,
                'gain_loss': entry.unrealized_gain_loss,
                'gain_loss_percentage': entry.unrealized_gain_loss_percentage
            })
        
        return JsonResponse({
            'success': True,
            'allocation_data': allocation_data,
            'performance_data': performance_data,
            'total_value': total_value,
            'total_invested': sum(float(entry.total_invested) for entry in portfolio_entries)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_http_methods(["POST"])
def quick_add_to_portfolio(request):
    """Quick add coin to portfolio with current market price"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please login to manage your portfolio'})
    
    try:
        data = json.loads(request.body)
        symbol = data.get('symbol', '').upper()
        amount = Decimal(str(data.get('amount', 0)))
        
        if not symbol or amount <= 0:
            return JsonResponse({'success': False, 'message': 'Invalid data'})

        try:
            coin = Coin.objects.get(symbol=symbol)
        except Coin.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Coin not found'})
        
        # Use current market price
        current_price = Decimal(str(coin.current_price))
        
        # Create buy transaction with current market price
        transaction = Transaction.objects.create(
            user=request.user,
            coin=coin,
            transaction_type='buy',
            amount=amount,
            price_per_coin=current_price,
            notes=f'Quick add at market price'
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Added {amount} {coin.symbol} to portfolio at ${current_price}',
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})
    except ValueError as e:
        return JsonResponse({'success': False, 'message': f'Invalid amount: {str(e)}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def settings(request):
    """Display user settings page"""
    from django.conf import settings as django_settings
    
    context = {
        'has_news_api_key': getattr(django_settings, 'NEWS_API_KEY', 'demo_key') != 'demo_key',
        'news_api_key_partial': getattr(django_settings, 'NEWS_API_KEY', 'demo_key')[:8] + '...' if getattr(django_settings, 'NEWS_API_KEY', 'demo_key') != 'demo_key' else 'Not configured',
    }
    
    if request.user.is_authenticated:
        # Get user statistics for authenticated users
        portfolio_count = Portfolio.objects.filter(user=request.user).count()
        watchlist_count = Watchlist.objects.filter(user=request.user).count()
        transaction_count = Transaction.objects.filter(user=request.user).count()
        
        context.update({
            'portfolio_count': portfolio_count,
            'watchlist_count': watchlist_count,
            'transaction_count': transaction_count,
        })
    
    return render(request, 'market/settings.html', context)


@require_http_methods(["POST"])
def update_settings(request):
    """Update user settings via API"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Authentication required'})
    
    try:
        data = json.loads(request.body)
        setting_type = data.get('type')
        
        if setting_type == 'clear_watchlist':
            # Clear user's watchlist
            Watchlist.objects.filter(user=request.user).delete()
            return JsonResponse({
                'success': True,
                'message': 'Watchlist cleared successfully'
            })
        
        elif setting_type == 'clear_portfolio':
            # Clear user's portfolio
            Portfolio.objects.filter(user=request.user).delete()
            Transaction.objects.filter(user=request.user).delete()
            return JsonResponse({
                'success': True,
                'message': 'Portfolio and transaction history cleared successfully'
            })
        
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid setting type'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})