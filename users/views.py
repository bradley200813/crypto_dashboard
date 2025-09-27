from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('users:login')
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def profile(request):
    from market.models import Portfolio, Watchlist, Transaction
    
    # Get user statistics
    portfolio_count = Portfolio.objects.filter(user=request.user).count()
    watchlist_count = Watchlist.objects.filter(user=request.user).count()
    transaction_count = Transaction.objects.filter(user=request.user).count()
    
    context = {
        'portfolio_count': portfolio_count,
        'watchlist_count': watchlist_count,
        'transaction_count': transaction_count,
    }
    
    return render(request, 'users/profile.html', context)
