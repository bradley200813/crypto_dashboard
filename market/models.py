from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

class Coin(models.Model):
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10, unique=True, db_index=True)  # Add index for fast lookups
    current_price = models.FloatField()
    market_cap = models.BigIntegerField(db_index=True)  # Index for sorting by market cap
    volume_24h = models.BigIntegerField()
    price_change_24h = models.FloatField(default=0.0)  # 24 hour price change percentage
    btc_dominance = models.FloatField()
    fear_greed = models.IntegerField()
    price_history = models.JSONField()  # store last 7 or 30 days price

    class Meta:
        indexes = [
            models.Index(fields=['market_cap']),
            models.Index(fields=['symbol']),
            models.Index(fields=['current_price']),
        ]

    def __str__(self):
        return self.name

class Watchlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    coin = models.ForeignKey(Coin, on_delete=models.CASCADE, db_index=True)
    date_added = models.DateTimeField(auto_now_add=True, null=True)

    class Meta:
        unique_together = ('user', 'coin')
        indexes = [
            models.Index(fields=['user', 'coin']),
            models.Index(fields=['date_added']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.coin.symbol}"

class Portfolio(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_index=True)
    coin = models.ForeignKey(Coin, on_delete=models.CASCADE, db_index=True)
    total_amount = models.DecimalField(max_digits=20, decimal_places=8, default=0)  # Total coins owned
    average_buy_price = models.DecimalField(max_digits=20, decimal_places=8, default=0)  # Average purchase price
    total_invested = models.DecimalField(max_digits=20, decimal_places=2, default=0, db_index=True)  # Total USD invested
    date_added = models.DateTimeField(auto_now_add=True, null=True)
    last_updated = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = ('user', 'coin')
        indexes = [
            models.Index(fields=['user', 'total_invested']),
            models.Index(fields=['last_updated']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.coin.symbol}: {self.total_amount}"

    @property
    def current_value(self):
        """Calculate current value of holdings"""
        return float(self.total_amount) * self.coin.current_price

    @property
    def unrealized_gain_loss(self):
        """Calculate unrealized profit/loss"""
        return self.current_value - float(self.total_invested)

    @property
    def unrealized_gain_loss_percentage(self):
        """Calculate unrealized profit/loss percentage"""
        if self.total_invested == 0:
            return 0
        return (self.unrealized_gain_loss / float(self.total_invested)) * 100

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('buy', 'Buy'),
        ('sell', 'Sell'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coin = models.ForeignKey(Coin, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=20, decimal_places=8)  # Amount of coins
    price_per_coin = models.DecimalField(max_digits=20, decimal_places=8)  # Price at time of transaction
    total_value = models.DecimalField(max_digits=20, decimal_places=2)  # Total transaction value in USD
    transaction_date = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.transaction_type.upper()} {self.amount} {self.coin.symbol} @ ${self.price_per_coin}"

    def save(self, *args, **kwargs):
        # Calculate total value if not provided
        if not self.total_value:
            self.total_value = self.amount * self.price_per_coin
        super().save(*args, **kwargs)

        # Update portfolio after transaction
        self.update_portfolio()

    def update_portfolio(self):
        """Update the user's portfolio based on this transaction"""
        portfolio, created = Portfolio.objects.get_or_create(
            user=self.user,
            coin=self.coin,
            defaults={
                'total_amount': 0,
                'average_buy_price': 0,
                'total_invested': 0
            }
        )

        if self.transaction_type == 'buy':
            # Calculate new average buy price
            current_value = float(portfolio.total_amount) * float(portfolio.average_buy_price)
            new_investment = float(self.total_value)
            new_total_amount = float(portfolio.total_amount) + float(self.amount)
            
            if new_total_amount > 0:
                new_average_price = (current_value + new_investment) / new_total_amount
                portfolio.average_buy_price = Decimal(str(new_average_price))
            
            portfolio.total_amount += self.amount
            portfolio.total_invested += self.total_value

        elif self.transaction_type == 'sell':
            portfolio.total_amount -= self.amount
            # Reduce total invested proportionally
            if float(portfolio.total_amount) >= 0:
                sell_ratio = float(self.amount) / (float(portfolio.total_amount) + float(self.amount))
                portfolio.total_invested -= portfolio.total_invested * Decimal(str(sell_ratio))
            else:
                portfolio.total_invested = 0

            # If all coins are sold, reset the portfolio
            if portfolio.total_amount <= 0:
                portfolio.total_amount = 0
                portfolio.average_buy_price = 0
                portfolio.total_invested = 0

        portfolio.save()

        # Delete portfolio entry if no coins left
        if portfolio.total_amount <= 0:
            portfolio.delete()
