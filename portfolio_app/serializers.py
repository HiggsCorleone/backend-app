from rest_framework import serializers
from .models import User, Portfolio, Stock, StockLot, Transaction,News

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

class UserSerializer(serializers.ModelSerializer):
    portfolio = PortfolioSerializer(read_only=True)
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'language',
            'portfolio', 'transaction_count'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def get_transaction_count(self, obj):
        return obj.transactions.count()

    def create(self, validated_data):
        # Create user and associated portfolio
        portfolio = Portfolio.objects.create()
        user = User.objects.create(
            portfolio=portfolio,
            **validated_data
        )
        return user
class NewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = News
        fields = ['id', 'title', 'date', 'description', 'created_at']