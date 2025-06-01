# content/urls.py
"""
Enhanced content URLs
"""

from django.urls import path, include
from . import views

app_name = 'content'

# Blog patterns
blog_patterns = [
    path('', views.BlogListView.as_view(), name='blog_list'),
    path('category/<slug:slug>/', views.BlogCategoryView.as_view(), name='blog_category'),
    path('tag/<slug:slug>/', views.BlogTagView.as_view(), name='blog_tag'),
    path('search/', views.BlogSearchView.as_view(), name='blog_search'),
    path('<slug:slug>/', views.BlogDetailView.as_view(), name='blog_detail'),
]

# Static page patterns
page_patterns = [
    path('tentang-kami/', views.AboutView.as_view(), name='about'),
    path('kontak/', views.ContactView.as_view(), name='contact'),
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('testimonial/', views.TestimonialsView.as_view(), name='testimonials'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy'),
    path('terms-of-service/', views.TermsOfServiceView.as_view(), name='terms'),
]

# API patterns
api_patterns = [
    path('contact/submit/', views.ContactSubmissionAPIView.as_view(), name='api_contact_submit'),
    path('newsletter/subscribe/', views.NewsletterSubscribeAPIView.as_view(), name='api_newsletter_subscribe'),
    path('testimonial/submit/', views.TestimonialSubmissionAPIView.as_view(), name='api_testimonial_submit'),
]

urlpatterns = [
    # Blog
    path('blog/', include(blog_patterns)),

    # Static pages
    path('', include(page_patterns)),

    # Dynamic pages
    path('page/<slug:slug>/', views.PageDetailView.as_view(), name='page_detail'),

    # API endpoints
    path('api/', include(api_patterns)),
]
