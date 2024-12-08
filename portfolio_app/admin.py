# admin.py
from django.contrib import admin
from .models import User, Portfolio, Stock,News, StockLot, Transaction

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'price', 'sector')
    search_fields = ('symbol', 'name')

@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = ('stock', 'portfolio', 'purchase_date', 'purchase_price', 'quantity', 'remaining_quantity')
    list_filter = ('stock', 'portfolio', 'purchase_date')

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('id', 'totalValue', 'last_updated')

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'language')
    search_fields = ('username', 'email')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'stock', 'quantity', 'price', 'date')
    list_filter = ('type', 'date', 'user')
    search_fields = ('user__username', 'stock__symbol')
@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'created_at')
    list_filter = ('date', 'created_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'date'