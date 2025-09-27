
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from .crypto_data_service import crypto_data_service
from .models import Coin

@ratelimit(key='user', rate='5/m', method='GET', block=True)
def data_status(request):
    """Get cryptocurrency data update status"""
    try:
        last_update = crypto_data_service.get_last_update_time()
        is_fresh = crypto_data_service.is_data_fresh(max_age_minutes=15)
        
        return JsonResponse({
            'success': True,
            'last_update': last_update.isoformat() if last_update else None,
            'is_fresh': is_fresh,
            'total_coins': Coin.objects.count(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@ratelimit(key='user', rate='2/h', method='POST', block=True)  # Limited to 2 per hour
@login_required
def update_crypto_data_view(request):
    """Trigger cryptocurrency data update (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({
            'success': False, 
            'message': 'Permission denied. Admin access required.'
        })
    
    try:
        # Check if update is needed
        if crypto_data_service.is_data_fresh(max_age_minutes=10):
            return JsonResponse({
                'success': False,
                'message': 'Data is fresh. Update not needed.',
                'last_update': crypto_data_service.get_last_update_time().isoformat()
            })
        
        # Perform update
        result = crypto_data_service.fetch_price_data()
        
        return JsonResponse({
            'success': result['success'],
            'message': result['message'],
            'updated_count': result.get('updated_count', 0),
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})