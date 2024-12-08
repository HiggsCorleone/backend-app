from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Import the views
from .views import (
    UserViewSet,
    PortfolioViewSet,
    StockViewSet,
    TransactionViewSet,
    NewsViewSet
)

# Initialize router
router = DefaultRouter()

# Register viewsets
router.register(r'users', UserViewSet)
router.register(r'portfolios', PortfolioViewSet)
router.register(r'stocks', StockViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'news', NewsViewSet)

# The API URLs are determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]