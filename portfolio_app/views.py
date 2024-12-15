from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from decimal import Decimal
from .models import News
from .serializers import NewsSerializer
import jwt
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from datetime import datetime, timedelta
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.contrib.auth.hashers import check_password
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .models import User, Portfolio, Stock, StockLot, Transaction
from .serializers import (
    UserSerializer, 
    PortfolioSerializer, 
    StockSerializer,
    TransactionSerializer,
    CustomTokenObtainPairSerializer,
    RegisterSerializer,
    StockLotSerializer,
    LoginSerializer
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
def generate_tokens(user):
    """Generate access and refresh tokens manually"""
    # Access token - expires in 1 hour
    access_payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=1),
        'type': 'access'
    }
    
    # Refresh token - expires in 1 day
    refresh_payload = {
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(days=1),
        'type': 'refresh'
    }
    
    access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
    refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
    
    return {
        'access': access_token,
        'refresh': refresh_token
    }

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens manually
        tokens = generate_tokens(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)

class LoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['email', 'password'],
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                'password': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )
    )
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        try:
            user = User.objects.get(email=email)
            # Use check_password to compare hashed password
            if check_password(password, user.password):
                tokens = generate_tokens(user)
                return Response({
                    'user': UserSerializer(user).data,
                    'tokens': tokens
                })
            else:
                return Response({'error': 'Invalid credentials'}, 
                              status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, 
                          status=status.HTTP_404_NOT_FOUND)

class LogoutView(generics.GenericAPIView):
    permission_classes = (AllowAny,)

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token to be invalidated')
            }
        ),
        responses={
            205: openapi.Response(
                description="The refresh token has been successfully invalidated."
            ),
            400: openapi.Response(
                description="Bad Request - invalid or missing refresh token."
            )
        },
        operation_description="Logout and invalidate the provided refresh token."
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            decoded_payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
            #user_id = decoded_payload['user_id']

            # Implement blacklist logic to store user_id as blacklisted
            # (e.g., database model or cache)

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response(
                {'error': 'Invalid or missing refresh token'},
                status=status.HTTP_400_BAD_REQUEST
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
    @swagger_auto_schema(
        method='post',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['symbol', 'quantity', 'price'],
            properties={
                'symbol': openapi.Schema(type=openapi.TYPE_STRING, description='Stock symbol'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of shares to buy'),
                'price': openapi.Schema(type=openapi.TYPE_NUMBER, description='Price per share')
            }
        ),
        responses={
            200: openapi.Response(
                description="Buy operation successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'transaction': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'lot': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'cash_balance': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'total_value': openapi.Schema(type=openapi.TYPE_NUMBER)
                    }
                )
            ),
            400: 'Bad Request',
            404: 'Stock not found'
        }
    )
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
    @swagger_auto_schema(
        method='post',
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['symbol', 'quantity', 'price'],
            properties={
                'symbol': openapi.Schema(type=openapi.TYPE_STRING, description='Stock symbol'),
                'quantity': openapi.Schema(type=openapi.TYPE_INTEGER, description='Number of shares to sell'),
                'price': openapi.Schema(type=openapi.TYPE_NUMBER, description='Price per share')
            }
        ),
        responses={
            200: openapi.Response(
                description="Sale operation successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'realized_gain': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'transactions': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                        'cash_balance': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'total_value': openapi.Schema(type=openapi.TYPE_NUMBER)
                    }
                )
            ),
            400: 'Bad Request - Not enough shares or invalid input',
            404: 'Stock not found'
        }
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