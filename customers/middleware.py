# customers/middleware.py
"""
Custom middleware for customer features
"""

from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .models import CustomerProfile


class CustomerProfileMiddleware(MiddlewareMixin):
    """Middleware to attach customer profile to request"""

    def process_request(self, request):
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            try:
                request.customer_profile = request.user.customerprofile
            except CustomerProfile.DoesNotExist:
                request.customer_profile = None
        else:
            request.customer_profile = None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers"""

    def process_response(self, request, response):
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response