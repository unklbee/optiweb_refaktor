# apps/services/views.py - Enhanced views with better performance
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, Prefetch, Avg, Count
from django.core.cache import cache
from django.core.paginator import Paginator
from django.http import JsonResponse
from meta.views import MetadataMixin
from apps.core.decorators import cache_response
from .models import Service, ServiceCategory, ServiceReview


class ServiceListView(MetadataMixin, ListView):
    """Enhanced service list view with filtering and search"""
    model = Service
    template_name = 'services/list.html'
    context_object_name = 'services'
    paginate_by = 12

    title = 'Layanan Service Laptop Bandung - Reparasi Semua Merk'
    description = 'Layanan service laptop lengkap di Bandung. Teknisi berpengalaman, garansi resmi, harga terjangkau untuk semua merk laptop.'

    def get_queryset(self):
        queryset = Service.objects.active().select_related('category').prefetch_related('tags')

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__name__icontains=search)
            ).distinct()

        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Brand filter
        brand_id = self.request.GET.get('brand')
        if brand_id:
            queryset = queryset.filter(
                Q(supported_brands__isnull=True) |
                Q(supported_brands__id=brand_id)
            ).distinct()

        # Sorting
        sort_by = self.request.GET.get('sort', 'popular')
        if sort_by == 'price_low':
            queryset = queryset.order_by('base_price_min')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-base_price_max')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-average_rating')
        elif sort_by == 'name':
            queryset = queryset.order_by('name')
        else:  # popular
            queryset = queryset.order_by('-popularity_score', '-is_featured')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Cache categories for 30 minutes
        cache_key = 'service_categories_active'
        categories = cache.get(cache_key)
        if categories is None:
            categories = ServiceCategory.objects.filter(is_active=True, show_in_menu=True)
            cache.set(cache_key, categories, 1800)

        context.update({
            'categories': categories,
            'selected_category': self.request.GET.get('category'),
            'search_query': self.request.GET.get('search'),
            'sort_by': self.request.GET.get('sort', 'popular'),
            'total_services': Service.objects.active().count(),
        })

        return context


class ServiceDetailView(MetadataMixin, DetailView):
    """Enhanced service detail view"""
    model = Service
    template_name = 'services/detail.html'
    context_object_name = 'service'

    def get_queryset(self):
        return Service.objects.active().select_related('category').prefetch_related(
            'tags',
            'supported_brands',
            Prefetch('reviews', queryset=ServiceReview.objects.filter(is_public=True)),
            'faqs'
        )

    def get_object(self):
        obj = super().get_object()
        # Increment popularity (with rate limiting)
        cache_key = f"service_view_{obj.id}_{self.request.session.session_key}"
        if not cache.get(cache_key):
            obj.increment_popularity()
            cache.set(cache_key, True, 3600)  # Once per hour per session
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.object

        # Related services (cached)
        cache_key = f"related_services_{service.id}"
        related_services = cache.get(cache_key)
        if related_services is None:
            related_services = Service.objects.active().filter(
                category=service.category
            ).exclude(id=service.id)[:4]
            cache.set(cache_key, related_services, 1800)

        # Service reviews with aggregation
        reviews = service.reviews.filter(is_public=True).order_by('-created_at')[:10]
        review_stats = service.reviews.filter(is_public=True).aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )

        # Price calculation for different scenarios
        price_scenarios = {
            'standard': service.get_price_range(),
            'express': service.get_price_range(priority='express'),
            'emergency': service.get_price_range(priority='emergency'),
        }

        context.update({
            'related_services': related_services,
            'reviews': reviews,
            'review_stats': review_stats,
            'price_scenarios': price_scenarios,
            'breadcrumbs': self.get_breadcrumbs(),
        })

        return context

    def get_breadcrumbs(self):
        service = self.object
        breadcrumbs = [
            {'name': 'Home', 'url': '/'},
            {'name': 'Layanan', 'url': '/layanan/'},
        ]

        if service.category:
            breadcrumbs.append({
                'name': service.category.name,
                'url': service.category.get_absolute_url()
            })

        breadcrumbs.append({
            'name': service.name,
            'url': service.get_absolute_url()
        })

        return breadcrumbs


@cache_response(timeout=1800)  # 30 minutes cache
def service_category_view(request, slug):
    """Enhanced category view with better performance"""
    category = get_object_or_404(ServiceCategory, slug=slug, is_active=True)

    services = Service.objects.active().filter(category=category).select_related('category')

    # Pagination
    paginator = Paginator(services, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Category statistics
    stats = {
        'total_services': services.count(),
        'avg_price_min': services.aggregate(avg=Avg('base_price_min'))['avg'] or 0,
        'avg_rating': ServiceReview.objects.filter(
            service__category=category, is_public=True
        ).aggregate(avg=Avg('rating'))['avg'] or 0,
    }

    context = {
        'category': category,
        'page_obj': page_obj,
        'services': page_obj.object_list,
        'stats': stats,
        'other_categories': ServiceCategory.objects.active().exclude(id=category.id)[:5],
    }

    return render(request, 'services/category.html', context)


# AJAX Views
def service_price_ajax(request, service_id):
    """AJAX endpoint for dynamic price calculation"""
    try:
        service = Service.objects.get(id=service_id, is_active=True)
        brand_id = request.GET.get('brand')
        priority = request.GET.get('priority', 'standard')

        brand = None
        if brand_id:
            from apps.core.models import Brand
            brand = Brand.objects.get(id=brand_id)

        price_range = service.get_price_range(brand=brand, priority=priority)
        estimated_duration = service.get_estimated_completion(priority)

        return JsonResponse({
            'success': True,
            'price_range': price_range,
            'estimated_duration': str(estimated_duration),
            'warranty_period': f"{service.warranty_period} hari",
        })

    except Service.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Service not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)