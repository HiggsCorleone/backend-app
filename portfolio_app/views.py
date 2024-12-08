from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal
from .models import News
from .serializers import NewsSerializer

from .models import User, Portfolio, Stock, StockLot, Transaction
from .serializers import (
    UserSerializer, 
    PortfolioSerializer, 
    StockSerializer,
    TransactionSerializer, 
    StockLotSerializer
)

class StockViewSet(viewsets.ModelViewSet):
    queryset = Stock.objects.all()
    serializer_class = StockSerializer

class PortfolioViewSet(viewsets.ModelViewSet):
    queryset = Portfolio.objects.all()
    serializer_class = PortfolioSerializer

    @action(detail=True, methods=['get'])
    def positions(self, request, pk=None):
        """Get all positions in the portfolio with their current returns"""
        portfolio = self.get_object()
        stocks = Stock.objects.filter(
            stocklot__portfolio=portfolio,
            stocklot__remaining_quantity__gt=0
        ).distinct()
        
        positions = []
        stock_value = Decimal(0)
        total_cost = Decimal(0)
        
        for stock in stocks:
            position = portfolio.calculate_position(stock)
            positions.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'current_price': stock.price,
                **position
            })
            stock_value += position['current_value']
            total_cost += position['total_cost']
        
        return Response({
            'positions': positions,
            'portfolio_summary': {
                'cash_balance': portfolio.cash_balance,
                'stock_value': stock_value,
                'total_value': portfolio.cash_balance + stock_value,
                'total_cost': total_cost,
                'total_gain': (portfolio.cash_balance + stock_value) - (10000 + total_cost),
                'return_percentage': 
                    (((portfolio.cash_balance + stock_value) - 10000) / 10000 * 100)
            }
        })

    @action(detail=True, methods=['post'])
    def buy(self, request, pk=None):
        """Buy stocks if user has enough cash"""
        portfolio = self.get_object()
        try:
            stock = Stock.objects.get(symbol=request.data['symbol'])
            quantity = int(request.data['quantity'])
            price = Decimal(request.data['price'])
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            total_cost = price * quantity
            if total_cost > portfolio.cash_balance:
                return Response(
                    {
                        'error': f'Insufficient funds. Cost: {total_cost} DT, Available: {portfolio.cash_balance} DT'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            lot = portfolio.buy_stock(stock, quantity, price)
            
            # Create transaction record
            transaction = Transaction.objects.create(
                user=portfolio.user,
                type='BUY',
                stock=stock,
                quantity=quantity,
                price=price,
                lot=lot
            )
            
            return Response({
                'status': 'purchase recorded',
                'transaction': TransactionSerializer(transaction).data,
                'lot': StockLotSerializer(lot).data,
                'cash_balance': portfolio.cash_balance,
                'total_value': portfolio.totalValue
            })
            
        except Stock.DoesNotExist:
            return Response(
                {'error': 'Stock not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def sell(self, request, pk=None):
        """Sell stocks using FIFO method"""
        portfolio = self.get_object()
        try:
            stock = Stock.objects.get(symbol=request.data['symbol'])
            quantity = int(request.data['quantity'])
            price = Decimal(request.data['price'])
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
                
            realized_gain, transactions = portfolio.sell_stock(stock, quantity, price)
            
            return Response({
                'status': 'sale recorded',
                'realized_gain': realized_gain,
                'transactions': TransactionSerializer(transactions, many=True).data,
                'cash_balance': portfolio.cash_balance,
                'total_value': portfolio.totalValue
            })
            
        except Stock.DoesNotExist:
            return Response(
                {'error': 'Stock not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    @action(detail=True, methods=['get'])
    def transaction_history(self, request, pk=None):
        """Get user's transaction history"""
        user = self.get_object()
        transactions = Transaction.objects.filter(user=user).order_by('-date')
        return Response(TransactionSerializer(transactions, many=True).data)

class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    
    def get_queryset(self):
        """Filter transactions by user if specified"""
        queryset = Transaction.objects.all()
        user_id = self.request.query_params.get('user_id', None)
        if user_id is not None:
            queryset = queryset.filter(user_id=user_id)
        return queryset.order_by('-date')
    
class NewsViewSet(viewsets.ModelViewSet):
    queryset = News.objects.all()
    serializer_class = NewsSerializer
    
    def get_queryset(self):
        """Optionally restricts the returned news by filtering"""
        queryset = News.objects.all()
        
        # Example of date filtering
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        
        if start_date is not None:
            queryset = queryset.filter(date__gte=start_date)
        if end_date is not None:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset.order_by('-date')
    
    @action(detail=False, methods=['delete'])
    def delete_all(self, request):
        """Delete all news records"""
        count = News.objects.count()
        News.objects.all().delete()
        return Response({
            'message': f'Successfully deleted {count} news records',
            'deleted_count': count
        }, status=status.HTTP_200_OK)


