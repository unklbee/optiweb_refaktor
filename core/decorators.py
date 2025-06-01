# apps/core/decorators.py - Custom decorators
from functools import wraps
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers


def ajax_required(view_func):
    """Decorator to ensure request is AJAX"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'AJAX request required'}, status=400)
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def customer_required(view_func):
    """Decorator to ensure user is a customer with profile"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('customers:login')

        if not hasattr(request.user, 'customerprofile'):
            # Create profile if doesn't exist
            from apps.customers.models import CustomerProfile
            CustomerProfile.objects.get_or_create(user=request.user)

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def staff_required(view_func):
    """Decorator to ensure user is staff"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff access required")
        return view_func(request, *args, **kwargs)

    return _wrapped_view


def rate_limit(rate='60/min'):
    """Rate limiting decorator"""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Parse rate limit
            limit, period = rate.split('/')
            limit = int(limit)

            if period == 'min':
                timeout = 60
            elif period == 'hour':
                timeout = 3600
            elif period == 'day':
                timeout = 86400
            else:
                timeout = 60

            # Get client identifier
            client_ip = request.META.get('REMOTE_ADDR')
            if request.user.is_authenticated:
                client_id = f"user_{request.user.id}"
            else:
                client_id = f"ip_{client_ip}"

            cache_key = f"rate_limit_{client_id}_{view_func.__name__}"
            current_requests = cache.get(cache_key, 0)

            if current_requests >= limit:
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'detail': f'Maximum {limit} requests per {period}'
                }, status=429)

            # Increment counter
            cache.set(cache_key, current_requests + 1, timeout)

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def cache_response(timeout=300, key_prefix='view'):
    """Custom cache decorator with dynamic key generation"""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Generate cache key
            cache_key_parts = [
                key_prefix,
                view_func.__name__,
                request.path,
                str(hash(frozenset(request.GET.items()))),
            ]

            if request.user.is_authenticated:
                cache_key_parts.append(f"user_{request.user.id}")

            cache_key = "_".join(cache_key_parts)

            # Try to get from cache
            response = cache.get(cache_key)
            if response is not None:
                return response

            # Generate response and cache it
            response = view_func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)

            return response

        return _wrapped_view

    return decorator
