# core/views.py
"""
Core views with improved architecture
"""

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.contrib.sites.shortcuts import get_current_site
from django.core.cache import cache

from .models import BusinessInfo, LaptopBrand
from services.models import Service, ServiceCategory
from content.models import FAQ, Testimonial


class HomeView(TemplateView):
    """Enhanced home view with caching"""

    template_name = 'core/home.html'

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Use cached data where possible
        context.update({
            'business_info': BusinessInfo.get_current(),
            'laptop_brands': LaptopBrand.get_supported_brands(),
            'featured_services': Service.get_featured_services(6),
            'featured_faqs': self.get_featured_faqs(),
            'featured_reviews': self.get_featured_reviews(),
            'page_title': self.get_page_title(),
            'meta_description': self.get_meta_description(),
        })

        return context

    def get_featured_faqs(self):
        """Get featured FAQs with caching"""
        cache_key = 'home:featured_faqs'
        faqs = cache.get(cache_key)

        if faqs is None:
            faqs = FAQ.objects.filter(is_featured=True)[:5]
            cache.set(cache_key, faqs, 60 * 30)  # Cache for 30 minutes

        return faqs

    def get_featured_reviews(self):
        """Get featured reviews with caching"""
        cache_key = 'home:featured_reviews'
        reviews = cache.get(cache_key)

        if reviews is None:
            reviews = Testimonial.objects.filter(
                is_featured=True,
                is_verified=True
            )[:3]
            cache.set(cache_key, reviews, 60 * 30)  # Cache for 30 minutes

        return reviews

    def get_page_title(self):
        """Get SEO optimized page title"""
        business_info = BusinessInfo.get_current()
        if business_info:
            return f"{business_info.business_name} | Service Laptop Bandung Terpercaya | Reparasi Laptop Profesional"
        return "Service Laptop Bandung Terpercaya | Reparasi Laptop Profesional"

    def get_meta_description(self):
        """Get SEO optimized meta description"""
        return ("Service laptop terpercaya di Bandung dengan teknisi berpengalaman. "
                "Garansi resmi, harga terjangkau, pickup & delivery. Melayani semua brand laptop.")

    def error_404(request, exception):
        """Custom 404 error page"""
        context = {
            'page_title': '404 - Halaman Tidak Ditemukan',
            'error_code': '404',
            'error_message': 'Halaman yang Anda cari tidak ditemukan.',
            'suggestions': [
                'Periksa kembali URL yang Anda masukkan',
                'Kembali ke halaman utama',
                'Gunakan menu navigasi untuk menemukan halaman yang Anda cari',
                'Hubungi kami jika Anda yakin ini adalah kesalahan'
            ]
        }
        return render(request, 'errors/404.html', context, status=404)

    def error_500(request):
        """Custom 500 error page"""
        context = {
            'page_title': '500 - Kesalahan Server',
            'error_code': '500',
            'error_message': 'Terjadi kesalahan pada server kami.',
            'suggestions': [
                'Coba refresh halaman dalam beberapa menit',
                'Hubungi customer service jika masalah berlanjut',
                'Kembali ke halaman utama'
            ]
        }
        return render(request, 'errors/500.html', context, status=500)

    def error_403(request, exception):
        """Custom 403 error page"""
        context = {
            'page_title': '403 - Akses Ditolak',
            'error_code': '403',
            'error_message': 'Anda tidak memiliki izin untuk mengakses halaman ini.',
            'suggestions': [
                'Login dengan akun yang memiliki izin',
                'Hubungi administrator jika Anda yakin ini adalah kesalahan',
                'Kembali ke halaman utama'
            ]
        }
        return render(request, 'errors/403.html', context, status=403)