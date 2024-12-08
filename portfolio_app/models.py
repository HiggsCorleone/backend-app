from django.db import models
from decimal import Decimal

class Stock(models.Model):
    id = models.AutoField(primary_key=True)
    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=20, decimal_places=2)
    sector = models.CharField(max_length=100)

    def __str__(self):
        return self.symbol

class StockLot(models.Model):
    portfolio = models.ForeignKey('Portfolio', on_delete=models.CASCADE, related_name='stock_lots')
    stock = models.ForeignKey('Stock', on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    purchase_price = models.DecimalField(max_digits=20, decimal_places=2)
    quantity = models.IntegerField()
    remaining_quantity = models.IntegerField()

    def __str__(self):
        return f"{self.stock.symbol} - {self.remaining_quantity}/{self.quantity} shares at {self.purchase_price} DT"

    class Meta:
        ordering = ['purchase_date']

class Portfolio(models.Model):
    id = models.AutoField(primary_key=True)
    cash_balance = models.DecimalField(max_digits=20, decimal_places=2, default=10000.0)
    totalValue = models.DecimalField(max_digits=20, decimal_places=2, default=10000.0)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Portfolio {self.id}"

    def calculate_position(self, stock):
        """Calculate current position and returns for a specific stock"""
        lots = StockLot.objects.filter(
            portfolio=self,
            stock=stock,
            remaining_quantity__gt=0
        ).order_by('purchase_date')
        
        total_shares = sum(lot.remaining_quantity for lot in lots)
        total_cost = sum(lot.purchase_price * lot.remaining_quantity for lot in lots)
        current_value = stock.price * total_shares
        
        if total_shares == 0:
            return {
                'shares': 0,
                'avg_cost': Decimal(0),
                'total_cost': Decimal(0),
                'current_value': Decimal(0),
                'unrealized_gain': Decimal(0),
                'return_percentage': Decimal(0)
            }
            
        avg_cost = total_cost / total_shares
        unrealized_gain = current_value - total_cost
        return_percentage = (unrealized_gain / total_cost * 100) if total_cost > 0 else Decimal(0)
        
        return {
            'shares': total_shares,
            'avg_cost': avg_cost,
            'total_cost': total_cost,
            'current_value': current_value,
            'unrealized_gain': unrealized_gain,
            'return_percentage': return_percentage,
            'lots': [
                {
                    'purchase_date': lot.purchase_date,
                    'shares': lot.remaining_quantity,
                    'price': lot.purchase_price,
                    'cost': lot.purchase_price * lot.remaining_quantity,
                    'current_value': stock.price * lot.remaining_quantity,
                    'gain': (stock.price - lot.purchase_price) * lot.remaining_quantity,
                    'return_percentage': ((stock.price - lot.purchase_price) / lot.purchase_price * 100)
                }
                for lot in lots
            ]
        }

    def calculate_total_value(self):
        """Calculate total portfolio value (cash + stocks)"""
        stock_value = sum(
            lot.stock.price * lot.remaining_quantity 
            for lot in self.stock_lots.filter(remaining_quantity__gt=0)
        )
        self.totalValue = self.cash_balance + stock_value
        self.save()
        return self.totalValue

    def buy_stock(self, stock, quantity, price):
        """Buy stocks if user has enough cash"""
        total_cost = price * quantity
        
        if total_cost > self.cash_balance:
            raise ValueError("Insufficient funds for this purchase")
            
        # Create new stock lot
        lot = StockLot.objects.create(
            portfolio=self,
            stock=stock,
            purchase_price=price,
            quantity=quantity,
            remaining_quantity=quantity
        )
        
        # Update cash balance
        self.cash_balance -= total_cost
        self.save()
        
        # Update total value
        self.calculate_total_value()
        return lot

    def sell_stock(self, stock, quantity, price):
        """Sell stocks using FIFO method"""
        lots = StockLot.objects.filter(
            portfolio=self,
            stock=stock,
            remaining_quantity__gt=0
        ).order_by('purchase_date')
        
        total_available = sum(lot.remaining_quantity for lot in lots)
        if quantity > total_available:
            raise ValueError(f"Not enough shares. You only have {total_available} shares available.")
        
        remaining_to_sell = quantity
        realized_gain = Decimal(0)
        transactions = []
        
        for lot in lots:
            if remaining_to_sell <= 0:
                break
                
            shares_from_lot = min(lot.remaining_quantity, remaining_to_sell)
            lot.remaining_quantity -= shares_from_lot
            lot.save()
            
            # Calculate realized gain
            realized_gain += (price - lot.purchase_price) * shares_from_lot
            remaining_to_sell -= shares_from_lot
            
            # Record transaction
            transactions.append(
                Transaction.objects.create(
                    user=self.user,
                    type='SELL',
                    stock=stock,
                    quantity=shares_from_lot,
                    price=price,
                    lot=lot
                )
            )
            
            # Add to cash balance
            self.cash_balance += price * shares_from_lot
            
        self.save()
        self.calculate_total_value()
        return realized_gain, transactions

class User(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    language = models.CharField(max_length=100)
    portfolio = models.OneToOneField(Portfolio, null=True, blank=True, on_delete=models.CASCADE, related_name='user')

    def __str__(self):
        return self.username

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    ]
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=4, choices=TRANSACTION_TYPES)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=20, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    lot = models.ForeignKey(StockLot, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.type} {self.quantity} shares of {self.stock.symbol}"

    class Meta:
        ordering = ['-date']


class News(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    date = models.DateField()  # Date of the news event
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Date when the news was added to the system

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "News"  # Correct plural form in admin

    def __str__(self):
        return self.title