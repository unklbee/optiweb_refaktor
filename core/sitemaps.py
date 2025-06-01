# core/sitemaps.py
"""
Enhanced sitemaps with better SEO
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from services.models import Service, ServiceCategory
from content.models import ContentPage


class StaticViewSitemap(Sitemap):
    """Static pages sitemap"""
    priority = 0.9
    changefreq = 'weekly'

    def items(self):
        return [
            'home',
            'content:about',
            'content:contact',
            'content:faq',
            'content:testimonials',
            'services:list',
        ]

    def location(self, item):
        return reverse(item)

    def lastmod(self, item):
        # Return recent date for static pages
        return timezone.now() - timedelta(days=1)


class ServiceSitemap(Sitemap):
    """Services sitemap"""
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Service.objects.filter(is_active=True, is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def priority(self, obj):
        # Higher priority for featured services
        return 0.9 if obj.is_featured else 0.7


class ServiceCategorySitemap(Sitemap):
    """Service categories sitemap"""
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return ServiceCategory.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse('services:category', args=[obj.slug])


class BlogSitemap(Sitemap):
    """Blog posts sitemap"""
    changefreq = "daily"
    priority = 0.6

    def items(self):
        return ContentPage.objects.filter(
            page_type='blog',
            is_published=True
        ).order_by('-publish_date')

    def lastmod(self, obj):
        return obj.updated_at

    def priority(self, obj):
        # Newer posts get higher priority
        days_old = (timezone.now() - obj.publish_date).days
        if days_old < 7:
            return 0.8
        elif days_old < 30:
            return 0.7
        else:
            return 0.5


class ContentSitemap(Sitemap):
    """Static content pages sitemap"""
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return ContentPage.objects.filter(
            page_type__in=['page', 'tutorial'],
            is_published=True
        )

    def lastmod(self, obj):
        return obj.updated_at


# Sitemaps registry
sitemaps = {
    'static': StaticViewSitemap,
    'services': ServiceSitemap,
    'categories': ServiceCategorySitemap,
    'blog': BlogSitemap,
    'content': ContentSitemap,
}