# market/urls.py
from django.urls import path
from . import views
from .data_views import data_status, update_crypto_data_view

app_name = 'market'  # optional, useful for namespacing

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Main dashboard
    path('', views.dashboard, name='index'),  # Alternative name for main dashboard
    path('watchlist/', views.watchlist, name='watchlist'),  # Watchlist page
    path('watchlist/api/', views.watchlist_api, name='watchlist_api'),  # Watchlist API data
    path('portfolio/', views.portfolio, name='portfolio'),  # Portfolio page
    path('news/', views.news, name='news'),  # News page
    path('coin/<str:symbol>/', views.coin_detail, name='coin_detail'),  # Coin detail page
    path('coin-data/<str:symbol>/', views.coin_data, name='coin_data'),  # AJAX for dynamic coin info
    path('watchlist/add/', views.add_to_watchlist, name='add_to_watchlist'),  # Add to watchlist
    path('watchlist/remove/', views.remove_from_watchlist, name='remove_from_watchlist'),  # Remove from watchlist
    path('watchlist/status/<str:symbol>/', views.get_watchlist_status, name='watchlist_status'),  # Check watchlist status
    path('portfolio/transaction/add/', views.add_transaction, name='add_transaction'),  # Add portfolio transaction
    path('portfolio/analytics/', views.portfolio_analytics, name='portfolio_analytics'),  # Portfolio analytics
    path('portfolio/quick-add/', views.quick_add_to_portfolio, name='quick_add_to_portfolio'),  # Quick add to portfolio
    path('api/toggle-watchlist/', views.toggle_watchlist, name='toggle_watchlist'),  # Toggle watchlist
    path('api/news/', views.get_filtered_news, name='get_filtered_news'),  # Get filtered news
    path('coins/search/', views.search_coins, name='search_coins'),  # Search for coins
    path('coins/filter/', views.get_filtered_coins, name='filter_coins'),  # Filter coins by category
    path('settings/', views.settings, name='settings'),  # Settings page
    path('api/settings/update/', views.update_settings, name='update_settings'),  # Update settings API
    path('api/data/status/', data_status, name='data_status'),  # Data update status
    path('api/data/update/', update_crypto_data_view, name='update_crypto_data'),  # Trigger data update
]
