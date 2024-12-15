from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

# Import the views
from .views import (
    UserViewSet,
    PortfolioViewSet,
    StockViewSet,
    TransactionViewSet,
    NewsViewSet,
    CustomTokenObtainPairView,
    RegisterView,
    LogoutView,
    LoginView
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
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', LoginView.as_view(), name='auth_login'),


    path('', include(router.urls)),
]