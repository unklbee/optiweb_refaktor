# apps/core/context_processors.py - Enhanced context processors
from django.conf import settings
from django.core.cache import cache
from .models import BusinessInfo, Brand
from apps.services.models import ServiceCategory


def business_info(request):
    """Make business info available globally with caching"""
    cache_key = 'global_business_info'
    business = cache.get(cache_key)

    if business is None:
        try:
            business = BusinessInfo.objects.filter(is_active=True).first()
            cache.set(cache_key, business, 3600)  # Cache for 1 hour
        except BusinessInfo.DoesNotExist:
            business = None

    return {'business_info': business}


def navigation_data(request):
    """Enhanced navigation data with caching"""
    cache_key = 'navigation_data'
    nav_data = cache.get(cache_key)

    if nav_data is None:
        nav_data = {
            'nav_service_categories': ServiceCategory.objects.filter(
                is_active=True
            ).order_by('order', 'name')[:6],
            'nav_brands': Brand.objects.filter(
                is_supported=True,
                is_active=True
            ).order_by('name')[:10],
            'nav_brand_count': Brand.objects.filter(
                is_supported=True,
                is_active=True
            ).count()
        }
        cache.set(cache_key, nav_data, 1800)  # Cache for 30 minutes

    return nav_data


def seo_globals(request):
    """Global SEO data and meta information"""
    return {
        'site_name': getattr(settings, 'SITE_NAME', 'Service Laptop Bandung'),
        'site_description': getattr(settings, 'SITE_DESCRIPTION',
                                    'Layanan service laptop terpercaya di Bandung dengan teknisi berpengalaman dan garansi resmi.'),
        'site_keywords': getattr(settings, 'SITE_KEYWORDS',
                                 'service laptop bandung, reparasi laptop bandung, teknisi laptop bandung'),
        'site_author': getattr(settings, 'SITE_AUTHOR', 'Service Laptop Bandung'),
        'canonical_url': request.build_absolute_uri(request.path),
        'current_year': timezone.now().year if 'timezone' in globals() else 2024,
    }


def user_context(request):
    """Enhanced user context with customer profile data"""
    context = {}

    if request.user.is_authenticated and hasattr(request.user, 'customerprofile'):
        profile = request.user.customerprofile
        context.update({
            'customer_profile': profile,
            'customer_points': profile.total_points,
            'membership_level': profile.membership_level,
            'member_discount': profile.get_discount_percentage(),
            'has_active_orders': profile.orders.filter(
                status__in=['PENDING', 'CONFIRMED', 'IN_PROGRESS', 'TESTING']
            ).exists() if hasattr(profile, 'orders') else False,
        })

    return context


def analytics_context(request):
    """Analytics and tracking context"""
    return {
        'google_analytics_id': getattr(settings, 'GOOGLE_ANALYTICS_ID', ''),
        'google_tag_manager_id': getattr(settings, 'GOOGLE_TAG_MANAGER_ID', ''),
        'facebook_pixel_id': getattr(settings, 'FACEBOOK_PIXEL_ID', ''),
        'enable_analytics': getattr(settings, 'ENABLE_ANALYTICS', not settings.DEBUG),
    }


def feature_flags(request):
    """Feature flags for conditional functionality"""
    return {
        'features': {
            'loyalty_program': True,
            'online_booking': True,
            'pickup_delivery': True,
            'live_chat': True,
            'mobile_app': False,
            'payment_gateway': False,
            'multi_language': False,
        }
    }


def device_context(request):
    """Device and browser detection context"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()

    is_mobile = any(device in user_agent for device in [
        'mobile', 'android', 'iphone', 'ipad', 'tablet'
    ])

    is_bot = any(bot in user_agent for bot in [
        'bot', 'crawler', 'spider', 'scraper'
    ])

    return {
        'is_mobile': is_mobile,
        'is_desktop': not is_mobile,
        'is_bot': is_bot,
        'user_agent': user_agent,
    }