# services/urls.py
"""
Enhanced services URLs with better structure
"""

from django.urls import path, include
from . import views

app_name = 'services'

# API patterns
api_patterns = [
    path('search/', views.ServiceAPIView.service_search, name='api_search'),
    path('<int:service_id>/details/', views.ServiceAPIView.service_details, name='api_details'),
    path('compare/', views.ServiceComparisonAPIView.as_view(), name='api_compare'),
    path('quote/', views.ServiceQuoteAPIView.as_view(), name='api_quote'),
]

urlpatterns = [
    # Main service pages
    path('', views.ServiceListView.as_view(), name='list'),
    path('kategori/<slug:slug>/', views.ServiceCategoryView.as_view(), name='category'),
    path('compare/', views.ServiceComparisonView.as_view(), name='compare'),
    path('quote/', views.ServiceQuoteView.as_view(), name='quote'),

    # Service detail (keep this last to avoid conflicts)
    path('<slug:slug>/', views.ServiceDetailView.as_view(), name='detail'),

    # API endpoints
    path('api/', include(api_patterns)),
]