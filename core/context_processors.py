# core/context_processors.py - Enhanced context processors
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import BusinessInfo, Brand


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
        try:
            from services.models import ServiceCategory

            nav_data = {
                'nav_service_categories': ServiceCategory.objects.filter(
                    is_active=True,
                    show_in_menu=True
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
        except Exception:
            nav_data = {
                'nav_service_categories': [],
                'nav_brands': [],
                'nav_brand_count': 0
            }

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
        'current_year': timezone.now().year,
    }


def user_context(request):
    """Enhanced user context with customer profile data"""
    context = {}

    if request.user.is_authenticated:
        try:
            if hasattr(request.user, 'customerprofile'):
                profile = request.user.customerprofile
                context.update({
                    'customer_profile': profile,
                    'customer_points': profile.total_points,
                    'membership_level': profile.membership_level,
                    'member_discount': profile.get_discount_percentage(),
                    'has_active_orders': profile.orders.filter(
                        status__in=['pending', 'confirmed', 'in_progress', 'testing']
                    ).exists(),
                    'unread_notifications': getattr(profile, 'notifications', None).filter(
                        is_read=False
                    ).count() if hasattr(profile, 'notifications') else 0,
                })
        except Exception:
            # Handle case where customer profile doesn't exist
            context.update({
                'customer_profile': None,
                'customer_points': 0,
                'membership_level': 'bronze',
                'member_discount': 0,
                'has_active_orders': False,
                'unread_notifications': 0,
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
            'customer_reviews': True,
            'blog_comments': True,
            'newsletter': True,
            'social_login': False,
            'two_factor_auth': False,
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


def notification_context(request):
    """Global notifications context"""
    context = {
        'global_notifications': [],
        'system_announcements': [],
    }

    # Add system-wide notifications
    try:
        from content.models import ContentPage

        # Get system announcements
        announcements = ContentPage.objects.filter(
            page_type='announcement',
            status='published',
            is_active=True,
            is_featured=True
        )[:3]

        context['system_announcements'] = announcements
    except Exception:
        pass

    return context


def cart_context(request):
    """Shopping cart context (for future e-commerce features)"""
    context = {
        'cart_items_count': 0,
        'cart_total': 0,
        'has_cart_items': False,
    }

    # This can be expanded when implementing shopping cart functionality
    if hasattr(request, 'session'):
        cart = request.session.get('cart', {})
        context.update({
            'cart_items_count': len(cart),
            'has_cart_items': len(cart) > 0,
        })

    return context


def maintenance_context(request):
    """Maintenance mode context"""
    return {
        'maintenance_mode': cache.get('maintenance_mode', False),
        'maintenance_message': cache.get('maintenance_message',
                                         'Sistem sedang dalam maintenance. Mohon coba lagi nanti.'),
    }


def contact_info_context(request):
    """Contact information context"""
    cache_key = 'contact_info_context'
    contact_info = cache.get(cache_key)

    if contact_info is None:
        try:
            business = BusinessInfo.objects.filter(is_active=True).first()
            if business:
                contact_info = {
                    'contact_phone': business.phone,
                    'contact_whatsapp': business.whatsapp,
                    'contact_email': business.email,
                    'business_address': business.address,
                    'business_hours': business.opening_hours,
                }
            else:
                contact_info = {
                    'contact_phone': '',
                    'contact_whatsapp': '',
                    'contact_email': '',
                    'business_address': '',
                    'business_hours': {},
                }
            cache.set(cache_key, contact_info, 3600)  # Cache for 1 hour
        except Exception:
            contact_info = {
                'contact_phone': '',
                'contact_whatsapp': '',
                'contact_email': '',
                'business_address': '',
                'business_hours': {},
            }

    return contact_info


def social_media_context(request):
    """Social media links context"""
    cache_key = 'social_media_context'
    social_media = cache.get(cache_key)

    if social_media is None:
        try:
            business = BusinessInfo.objects.filter(is_active=True).first()
            if business and business.social_media:
                social_media = {
                    'social_media_links': business.social_media,
                    'has_social_media': bool(business.social_media),
                }
            else:
                social_media = {
                    'social_media_links': {},
                    'has_social_media': False,
                }
            cache.set(cache_key, social_media, 3600)  # Cache for 1 hour
        except Exception:
            social_media = {
                'social_media_links': {},
                'has_social_media': False,
            }

    return social_media