"""
URL configuration for optiontech_web_v2 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from django.http import HttpResponse

from core.sitemaps import sitemaps
from core.views import HomeView


def robots_txt(request):
    """Generate robots.txt dynamically"""
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]

    if not settings.DEBUG:
        # Add crawl delay for production
        lines.insert(2, "Crawl-delay: 1")

    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # Core pages
    path('', HomeView.as_view(), name='home'),

    # Services
    path('layanan/', include('services.urls')),

    # Content pages
    path('', include('content.urls')),

    # Customer portal
    path('customer/', include('customers.urls')),

    # API endpoints
    path('api/v1/', include('api.urls')),

    # SEO and utilities
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots_txt'),

    # CKEditor
    path('ckeditor/', include('ckeditor_uploader.urls')),

    # Health check
    path('health/', TemplateView.as_view(
        template_name='core/health.html',
        extra_context={'status': 'ok'}
    ), name='health_check'),
]

# Error pages
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'
handler403 = 'core.views.error_403'

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Add debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
                          path('__debug__/', include(debug_toolbar.urls)),
                      ] + urlpatterns