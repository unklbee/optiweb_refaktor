# Content Views Enhancement
from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib import messages
from meta.views import MetadataMixin
from apps.core.decorators import cache_response, rate_limit
from .forms import ContactForm, TestimonialForm


class ContentListView(MetadataMixin, ListView):
    """Enhanced content listing with advanced filtering"""
    model = ContentPage
    template_name = 'content/list.html'
    context_object_name = 'pages'
    paginate_by = 12

    def get_queryset(self):
        queryset = ContentPage.published.select_related('author', 'category').prefetch_related('tags')

        # Filter by type
        content_type = self.kwargs.get('content_type', 'blog')
        queryset = queryset.filter(page_type=content_type)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(excerpt__icontains=search) |
                Q(tags__name__icontains=search)
            ).distinct()

        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        # Tag filter
        tag = self.request.GET.get('tag')
        if tag:
            queryset = queryset.filter(tags__name__icontains=tag)

        # Sorting
        sort_by = self.request.GET.get('sort', 'latest')
        if sort_by == 'popular':
            queryset = queryset.order_by('-view_count')
        elif sort_by == 'oldest':
            queryset = queryset.order_by('publish_date')
        else:  # latest
            queryset = queryset.order_by('-publish_date')

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        content_type = self.kwargs.get('content_type', 'blog')

        context.update({
            'content_type': content_type,
            'categories': ContentCategory.objects.filter(
                pages__page_type=content_type,
                pages__status=ContentPage.Status.PUBLISHED
            ).annotate(count=Count('pages')).distinct(),
            'popular_tags': ContentPage.published.filter(
                page_type=content_type
            ).values('tags__name').annotate(
                count=Count('tags')
            ).order_by('-count')[:10],
            'featured_content': ContentPage.featured.filter(
                page_type=content_type
            )[:3] if content_type == 'blog' else None,
        })

        return context


@cache_response(timeout=3600)  # Cache for 1 hour
def faq_view(request):
    """Enhanced FAQ view with search and analytics"""
    # Get all FAQs grouped by category
    faqs_by_category = {}
    for category_code, category_name in FAQ.Category.choices:
        faqs = FAQ.objects.filter(
            category=category_code,
            is_active=True
        ).order_by('order_priority')

        if faqs.exists():
            faqs_by_category[category_name] = faqs

    # Search functionality
    search_query = request.GET.get('search')
    if search_query:
        search_results = FAQ.objects.filter(
            Q(question__icontains=search_query) |
            Q(answer__icontains=search_query),
            is_active=True
        ).order_by('-helpful_count', 'order_priority')
    else:
        search_results = None

    # Featured FAQs for homepage
    featured_faqs = FAQ.objects.filter(
        is_featured=True,
        is_active=True
    ).order_by('order_priority')[:5]

    context = {
        'faqs_by_category': faqs_by_category,
        'search_results': search_results,
        'search_query': search_query,
        'featured_faqs': featured_faqs,
        'total_faqs': FAQ.objects.filter(is_active=True).count(),
    }

    return render(request, 'content/faq.html', context)


@rate_limit('5/min')  # Rate limit contact form submissions
def contact_view(request):
    """Enhanced contact form with validation and tracking"""
    if request.method == 'POST':
        form = ContactForm(request.POST, request.FILES)
        if form.is_valid():
            # Create submission
            submission = form.save(commit=False)

            # Add tracking data
            submission.ip_address = request.META.get('REMOTE_ADDR')
            submission.user_agent = request.META.get('HTTP_USER_AGENT', '')
            submission.referrer_url = request.META.get('HTTP_REFERER', '')

            submission.save()

            # Send notification to admin
            from apps.core.utils import NotificationService
            NotificationService.send_email_notification(
                subject=f"New Contact: {submission.get_inquiry_type_display()}",
                template_name='emails/contact_notification.html',
                context={'submission': submission},
                recipient_list=['admin@servicelaptopmandung.com']
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Pesan berhasil dikirim! Kami akan segera menghubungi Anda.'
                })

            messages.success(request, 'Pesan berhasil dikirim!')
            return redirect('content:contact')

        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                })
    else:
        form = ContactForm()

    context = {
        'form': form,
        'page_title': 'Kontak Kami - Service Laptop Bandung',
        'meta_description': 'Hubungi service laptop terpercaya di Bandung. Konsultasi gratis, respons cepat, layanan pickup & delivery tersedia.'
    }

    return render(request, 'content/contact.html', context) * *kwargs):
    if not self.slug:
        from django.utils.text import slugify
    self.slug = slugify(self.name)
    super().save(*args, **kwargs) @property
    def

    full_path(self):
        """Get full category path"""
        if self.parent:
            return f"{self.parent.full_path} > {self.name}"
        return self.name


class ContentPage(TimestampedModel, ModelMeta, CacheableMixin):
    """Enhanced content page model for CMS"""

    class PageType(models.TextChoices):
        BLOG = 'blog', 'Blog Post'
        PAGE = 'page', 'Static Page'
        NEWS = 'news', 'News Article'
        TUTORIAL = 'tutorial', 'Tutorial'
        CASE_STUDY = 'case_study', 'Case Study'
        FAQ = 'faq', 'FAQ Page'
        LANDING = 'landing', 'Landing Page'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        REVIEW = 'review', 'Under Review'
        PUBLISHED = 'published', 'Published'
        ARCHIVED = 'archived', 'Archived'

    # Basic Information
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    page_type = models.CharField(
        max_length=20,
        choices=PageType.choices,
        default=PageType.BLOG
    )
    category = models.ForeignKey(
        ContentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pages'
    )

    # Content
    excerpt = models.TextField(
        max_length=500,
        blank=True,
        help_text="Brief summary for listings and previews"
    )
    content = RichTextField()
    table_of_contents = models.JSONField(
        default=list,
        help_text="Auto-generated TOC from headings"
    )

    # Media
    featured_image = models.ImageField(
        upload_to='content/',
        blank=True,
        null=True
    )
    featured_image_alt = models.CharField(
        max_length=255,
        blank=True,
        help_text="Alt text for featured image"
    )
    gallery_images = models.JSONField(
        default=list,
        help_text="Additional images for content"
    )

    # Authoring
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authored_content'
    )
    co_authors = models.ManyToManyField(
        User,
        blank=True,
        related_name='co_authored_content'
    )

    # Publishing
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True
    )
    publish_date = models.DateTimeField(null=True, blank=True)
    featured_until = models.DateTimeField(null=True, blank=True)

    # SEO & Marketing
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(max_length=160, blank=True)
    target_keyword = models.CharField(max_length=255, blank=True)
    secondary_keywords = models.JSONField(default=list)
    focus_keyphrase = models.CharField(max_length=255, blank=True)

    # Social Media
    social_title = models.CharField(max_length=255, blank=True)
    social_description = models.TextField(max_length=300, blank=True)
    social_image = models.ImageField(
        upload_to='content/social/',
        blank=True,
        null=True
    )

    # Display Settings
    is_featured = models.BooleanField(default=False, db_index=True)
    show_in_menu = models.BooleanField(default=False)
    menu_order = models.PositiveIntegerField(default=0)
    template_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Custom template for this page"
    )

    # Analytics & Engagement
    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    share_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    reading_time = models.PositiveIntegerField(
        default=0,
        help_text="Estimated reading time in minutes"
    )

    # Content Settings
    allow_comments = models.BooleanField(default=True)
    password_protected = models.BooleanField(default=False)
    password = models.CharField(max_length=100, blank=True)

    # Related Content
    related_pages = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='related_to'
    )
    related_services = models.ManyToManyField(
        'services.Service',
        blank=True,
        related_name='related_content'
    )

    # Tags
    tags = TaggableManager(blank=True)

    # Django-meta configuration
    _metadata = {
        'title': 'get_meta_title',
        'description': 'get_meta_description',
        'keywords': 'get_meta_keywords',
        'image': 'get_meta_image',
    }

    class Meta:
        ordering = ['-publish_date', '-created_at']
        indexes = [
            models.Index(fields=['status', 'page_type']),
            models.Index(fields=['is_featured', 'publish_date']),
            models.Index(fields=['author', 'status']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args,