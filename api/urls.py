# api/urls.py (New API app for better organization)
"""
API URLs for the application
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# DRF Router for ViewSets
router = DefaultRouter()
router.register(r'services', views.ServiceViewSet)
router.register(r'categories', views.ServiceCategoryViewSet)
router.register(r'orders', views.ServiceOrderViewSet, basename='order')
router.register(r'reviews', views.ServiceReviewViewSet)

# API v1 patterns
v1_patterns = [
    # Authentication
    path('auth/login/', views.LoginAPIView.as_view(), name='login'),
    path('auth/logout/', views.LogoutAPIView.as_view(), name='logout'),
    path('auth/register/', views.RegisterAPIView.as_view(), name='register'),
    path('auth/profile/', views.ProfileAPIView.as_view(), name='profile'),

    # Services
    path('services/search/', views.ServiceSearchAPIView.as_view(), name='service_search'),
    path('services/popular/', views.PopularServicesAPIView.as_view(), name='popular_services'),
    path('services/compare/', views.ServiceCompareAPIView.as_view(), name='service_compare'),

    # Orders
    path('orders/create/', views.CreateOrderAPIView.as_view(), name='create_order'),
    path('orders/track/<str:order_number>/', views.TrackOrderAPIView.as_view(), name='track_order'),

    # Loyalty
    path('loyalty/points/', views.PointsBalanceAPIView.as_view(), name='points_balance'),
    path('loyalty/rewards/', views.AvailableRewardsAPIView.as_view(), name='available_rewards'),
    path('loyalty/redeem/', views.RedeemRewardAPIView.as_view(), name='redeem_reward'),

    # Utilities
    path('contact/', views.ContactAPIView.as_view(), name='contact'),
    path('quote/', views.ServiceQuoteAPIView.as_view(), name='service_quote'),
    path('health/', views.HealthCheckAPIView.as_view(), name='health_check'),

    # DRF router URLs
    path('', include(router.urls)),
]

urlpatterns = [
    path('v1/', include(v1_patterns)),

    # API documentation
    path('docs/', views.api_documentation, name='api_docs'),
    path('schema/', views.api_schema, name='api_schema'),
]