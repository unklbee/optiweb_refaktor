# ================================
# CORE MIDDLEWARE & CONTEXT PROCESSORS
# ================================

# apps/core/middleware.py - Custom middleware
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from .models import BusinessInfo

logger = logging.getLogger(__name__)


class RequestLogMiddleware(MiddlewareMixin):
    """Middleware to log request details and performance"""

    def process_request(self, request):
        request._start_time = time.time()

        # Log request details
        logger.info(f"Request: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')}")
        return None

    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time

            # Log slow requests (> 1 second)
            if duration > 1.0:
                logger.warning(f"Slow request: {request.path} took {duration:.2f}s")

            # Add performance header
            response['X-Response-Time'] = f"{duration:.3f}s"

        return response


class BusinessInfoMiddleware(MiddlewareMixin):
    """Middleware to add business info to all requests"""

    def process_request(self, request):
        # Cache business info for 1 hour
        cache_key = 'business_info_middleware'
        business_info = cache.get(cache_key)

        if business_info is None:
            try:
                business_info = BusinessInfo.objects.filter(is_active=True).first()
                cache.set(cache_key, business_info, 3600)
            except:
                business_info = None

        request.business_info = business_info
        return None


class APIThrottleMiddleware(MiddlewareMixin):
    """Simple API rate limiting middleware"""

    def process_request(self, request):
        if request.path.startswith('/api/'):
            # Get client IP
            client_ip = self.get_client_ip(request)
            cache_key = f"api_throttle_{client_ip}"

            # Check request count in last minute
            request_count = cache.get(cache_key, 0)

            if request_count > 60:  # 60 requests per minute
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'detail': 'Too many requests. Please try again later.'
                }, status=429)

            # Increment counter
            cache.set(cache_key, request_count + 1, 60)

        return None

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to responses"""

    def process_response(self, request, response):
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # CSP header for non-admin pages
        if not request.path.startswith('/admin/'):
            response['Content-Security-Policy'] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://cdnjs.cloudflare.com; "
                "connect-src 'self';"
            )

        return response


class MaintenanceModeMiddleware(MiddlewareMixin):
    """Maintenance mode middleware"""

    def process_request(self, request):
        # Check if maintenance mode is enabled
        maintenance_mode = cache.get('maintenance_mode', False)

        if maintenance_mode:
            # Allow admin and staff access
            if (request.user.is_authenticated and
                    (request.user.is_staff or request.user.is_superuser)):
                return None

            # Allow access to admin and maintenance pages
            allowed_paths = ['/admin/', '/maintenance/', '/health/']
            if any(request.path.startswith(path) for path in allowed_paths):
                return None

            # Return maintenance page for others
            from django.shortcuts import render
            return render(request, 'maintenance.html', status=503)

        return None