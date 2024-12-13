from rest_framework import serializers
from .models import User, Portfolio, Stock, StockLot, Transaction,News
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
from rest_framework_simplejwt.tokens import RefreshToken

class StockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ['id', 'symbol', 'name', 'price', 'sector']

class StockLotSerializer(serializers.ModelSerializer):
    stock = StockSerializer(read_only=True)
    current_value = serializers.SerializerMethodField()
    unrealized_gain = serializers.SerializerMethodField()
    return_percentage = serializers.SerializerMethodField()

    class Meta:
        model = StockLot
        fields = [
            'id', 'stock', 'purchase_date', 'purchase_price',
            'quantity', 'remaining_quantity', 'current_value',
            'unrealized_gain', 'return_percentage'
        ]

    def get_current_value(self, obj):
        return obj.stock.price * obj.remaining_quantity

    def get_unrealized_gain(self, obj):
        return (obj.stock.price - obj.purchase_price) * obj.remaining_quantity

    def get_return_percentage(self, obj):
        if obj.purchase_price == 0:
            return 0
        return ((obj.stock.price - obj.purchase_price) / obj.purchase_price) * 100

class PortfolioSerializer(serializers.ModelSerializer):
    stock_lots = StockLotSerializer(many=True, read_only=True)
    positions = serializers.SerializerMethodField()

    class Meta:
        model = Portfolio
        fields = ['id', 'totalValue', 'last_updated', 'stock_lots', 'positions']

    def get_positions(self, obj):
        positions = []
        stocks = Stock.objects.filter(
            stocklot__portfolio=obj,
            stocklot__remaining_quantity__gt=0
        ).distinct()

        for stock in stocks:
            position = obj.calculate_position(stock)
            positions.append({
                'symbol': stock.symbol,
                'name': stock.name,
                'current_price': stock.price,
                **position
            })
        return positions

class TransactionSerializer(serializers.ModelSerializer):
    stock = StockSerializer(read_only=True)
    stock_symbol = serializers.CharField(write_only=True)
    lot_details = StockLotSerializer(source='lot', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'user', 'type', 'stock', 'stock_symbol',
            'quantity', 'price', 'date', 'lot_details'
        ]
        read_only_fields = ['stock', 'lot_details']

    def create(self, validated_data):
        stock_symbol = validated_data.pop('stock_symbol')
        try:
            stock = Stock.objects.get(symbol=stock_symbol)
            validated_data['stock'] = stock
            return super().create(validated_data)
        except Stock.DoesNotExist:
            raise serializers.ValidationError(
                {'stock_symbol': 'Stock not found'}
            )
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Add extra responses
        data['username'] = self.user.username
        data['email'] = self.user.email
        data['language'] = self.user.language
        if self.user.portfolio:
            data['portfolio_id'] = self.user.portfolio.id
        return data

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'language']

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        # Remove password confirmation field
        validated_data.pop('password2')
        
        # Hash the password
        validated_data['password'] = make_password(validated_data['password'])
        
        # Create portfolio
        portfolio = Portfolio.objects.create()
        
        # Create user with hashed password and portfolio
        user = User.objects.create(
            portfolio=portfolio,
            **validated_data
        )
        
        return user

class UserSerializer(serializers.ModelSerializer):
    portfolio = PortfolioSerializer(read_only=True)
    transaction_count = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'language',
            'portfolio', 'transaction_count', 'password',
            'confirm_password'
        ]

    def get_transaction_count(self, obj):
        return obj.transactions.count()

    def validate(self, data):
        # Password validation
        if 'password' in data:
            if len(data['password']) < 8:
                raise ValidationError("Password must be at least 8 characters long")
            
            if data['password'] != data.pop('confirm_password', None):
                raise ValidationError("Passwords do not match")

        return data

    def create(self, validated_data):
        # Hash password and create user
        validated_data['password'] = make_password(validated_data['password'])
        
        # Create portfolio first
        portfolio = Portfolio.objects.create()
        
        # Create user with portfolio
        user = User.objects.create(
            portfolio=portfolio,
            **validated_data
        )
        return user

    def update(self, instance, validated_data):
        # Handle password updates
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        
        return super().update(instance, validated_data)
    

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email', None)
        password = data.get('password', None)

        if email is None:
            raise ValidationError("An email address is required to login")

        if password is None:
            raise ValidationError("A password is required to login")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("User with this email does not exist")

        if not check_password(password, user.password):
            raise ValidationError("Incorrect password")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return {
            'user': user,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ['id', 'title', 'date', 'description', 'created_at']