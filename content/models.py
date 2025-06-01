# content/models.py - Enhanced content management
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from ckeditor.fields import RichTextField
from taggit.managers import TaggableManager
from meta.models import ModelMeta
from core.models import TimestampedModel, CacheableMixin
from core.utils import SEOHelper
from decimal import Decimal
import uuid


class ContentCategory(TimestampedModel):
    """Categories for content organization"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6")
    icon = models.CharField(max_length=255, blank=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "Content Categories"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def full_path(self):
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

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)

        # Auto-generate excerpt if not provided
        if not self.excerpt and self.content:
            self.excerpt = SEOHelper.generate_meta_description(self.content, 300)

        # Calculate reading time
        if self.content:
            word_count = len(self.content.split())
            self.reading_time = max(1, round(word_count / 200))  # 200 WPM average

        # Set publish date when status changes to published
        if self.status == self.Status.PUBLISHED and not self.publish_date:
            from django.utils import timezone
            self.publish_date = timezone.now()

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        if self.page_type == self.PageType.BLOG:
            return reverse('content:blog_detail', kwargs={'slug': self.slug})
        elif self.page_type == self.PageType.NEWS:
            return reverse('content:news_detail', kwargs={'slug': self.slug})
        return reverse('content:page_detail', kwargs={'slug': self.slug})

    # SEO Methods
    def get_meta_title(self):
        if self.meta_title:
            return self.meta_title
        return SEOHelper.generate_meta_title(self.title)

    def get_meta_description(self):
        if self.meta_description:
            return self.meta_description
        return SEOHelper.generate_meta_description(self.excerpt or self.content)

    def get_meta_keywords(self):
        keywords = ['service laptop bandung']
        if self.target_keyword:
            keywords.append(self.target_keyword)
        keywords.extend(self.secondary_keywords)
        keywords.extend([tag.name for tag in self.tags.all()])
        return keywords

    def get_meta_image(self):
        if self.social_image:
            return self.social_image.url
        elif self.featured_image:
            return self.featured_image.url
        return None

    # Utility Methods
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    def increment_view_count(self):
        """Increment view count (use with rate limiting)"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def get_estimated_read_time(self):
        """Get human-readable reading time"""
        if self.reading_time <= 1:
            return "1 min read"
        return f"{self.reading_time} min read"

    @property
    def is_recent(self):
        """Check if content was published recently (within 7 days)"""
        if not self.publish_date:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() - self.publish_date <= timedelta(days=7)


class FAQ(TimestampedModel):
    """Enhanced FAQ model with categorization"""

    class Category(models.TextChoices):
        GENERAL = 'general', 'Umum'
        PRICING = 'pricing', 'Harga & Pembayaran'
        WARRANTY = 'warranty', 'Garansi'
        SERVICE = 'service', 'Layanan'
        TECHNICAL = 'technical', 'Teknis'
        PICKUP = 'pickup', 'Pickup & Delivery'
        PARTS = 'parts', 'Spare Parts'
        ACCOUNT = 'account', 'Akun Customer'

    question = models.CharField(max_length=500)
    answer = RichTextField()
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
        db_index=True
    )

    # Display Settings
    order_priority = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first"
    )
    is_featured = models.BooleanField(
        default=False,
        help_text="Show on homepage/important pages"
    )

    # SEO
    slug = models.SlugField(unique=True, blank=True)
    meta_description = models.TextField(max_length=160, blank=True)

    # Analytics
    view_count = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)

    # Related Content
    related_services = models.ManyToManyField(
        'services.Service',
        blank=True,
        help_text="Services related to this FAQ"
    )
    related_faqs = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False
    )

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['category', 'order_priority', 'question']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['is_featured', 'order_priority']),
        ]

    def __str__(self):
        return self.question[:100]

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.question[:50])
            self.slug = base_slug

            # Ensure uniqueness
            counter = 1
            while FAQ.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('content:faq_detail', kwargs={'slug': self.slug})

    @property
    def helpfulness_ratio(self):
        """Calculate helpfulness percentage"""
        total = self.helpful_count + self.not_helpful_count
        return (self.helpful_count / total * 100) if total > 0 else 0


class Testimonial(TimestampedModel):
    """Enhanced testimonial model with rich features"""

    class ServiceType(models.TextChoices):
        HARDWARE_REPAIR = 'hardware', 'Hardware Repair'
        SOFTWARE_INSTALL = 'software', 'Software Installation'
        CLEANING = 'cleaning', 'Laptop Cleaning'
        UPGRADE = 'upgrade', 'Hardware Upgrade'
        DATA_RECOVERY = 'recovery', 'Data Recovery'
        GENERAL = 'general', 'General Service'

    # Customer Information
    customer_name = models.CharField(max_length=100)
    customer_email = models.EmailField(blank=True)
    customer_photo = models.ImageField(
        upload_to='testimonials/',
        blank=True,
        null=True
    )
    customer_location = models.CharField(max_length=100, blank=True)
    customer_occupation = models.CharField(max_length=100, blank=True)

    # Device & Service Information
    laptop_brand = models.ForeignKey(
        'core.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    laptop_model = models.CharField(max_length=100, blank=True)
    service_type = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        default=ServiceType.GENERAL
    )
    service_date = models.DateField(null=True, blank=True)

    # Review Content
    rating = models.PositiveIntegerField(
        choices=[(i, f"{i} Stars") for i in range(1, 6)],
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200, blank=True)
    review_text = models.TextField()

    # Additional Details
    pros = models.JSONField(
        default=list,
        help_text="List of positive aspects"
    )
    cons = models.JSONField(
        default=list,
        help_text="List of negative aspects (for internal use)"
    )

    # Media
    before_images = models.JSONField(default=list)
    after_images = models.JSONField(default=list)
    video_url = models.URLField(blank=True)

    # Verification & Moderation
    is_verified = models.BooleanField(
        default=False,
        help_text="Customer and service verified"
    )
    verification_method = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email Verification'),
            ('phone', 'Phone Verification'),
            ('order', 'Order Number Verification'),
            ('manual', 'Manual Verification')
        ],
        blank=True
    )
    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)

    # SEO
    slug = models.SlugField(unique=True, blank=True)

    # Analytics
    helpful_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)

    # Related Order
    order = models.OneToOneField(
        'customers.ServiceOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='testimonial'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_verified', 'is_public']),
            models.Index(fields=['rating', 'is_featured']),
            models.Index(fields=['service_type', 'laptop_brand']),
        ]

    def __str__(self):
        return f"{self.customer_name} - {self.rating}★ - {self.title or self.review_text[:50]}"

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(f"{self.customer_name}-{self.rating}-star")
            self.slug = base_slug

            # Ensure uniqueness
            counter = 1
            while Testimonial.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('content:testimonial_detail', kwargs={'slug': self.slug})

    def get_star_range(self):
        """Return range for template loops"""
        return range(self.rating)

    def get_empty_star_range(self):
        """Return range for empty stars"""
        return range(5 - self.rating)

    @property
    def star_percentage(self):
        """Get star rating as percentage"""
        return (self.rating / 5) * 100


class ContactSubmission(TimestampedModel):
    """Enhanced contact form submissions"""

    class InquiryType(models.TextChoices):
        SERVICE = 'service', 'Service Inquiry'
        QUOTE = 'quote', 'Price Quote'
        SUPPORT = 'support', 'Technical Support'
        COMPLAINT = 'complaint', 'Complaint'
        SUGGESTION = 'suggestion', 'Suggestion'
        PARTNERSHIP = 'partnership', 'Partnership'
        GENERAL = 'general', 'General Question'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        MEDIUM = 'medium', 'Medium'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    class Status(models.TextChoices):
        NEW = 'new', 'New'
        ASSIGNED = 'assigned', 'Assigned'
        IN_PROGRESS = 'in_progress', 'In Progress'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    # Contact Information
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)

    # Inquiry Details
    inquiry_type = models.CharField(
        max_length=20,
        choices=InquiryType.choices,
        default=InquiryType.GENERAL
    )
    subject = models.CharField(max_length=200)
    message = models.TextField()

    # Device Information (for service inquiries)
    laptop_brand = models.ForeignKey(
        'core.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    laptop_model = models.CharField(max_length=100, blank=True)
    device_age = models.CharField(
        max_length=20,
        choices=[
            ('new', 'Less than 1 year'),
            ('1-2', '1-2 years'),
            ('2-3', '2-3 years'),
            ('3-5', '3-5 years'),
            ('old', 'More than 5 years')
        ],
        blank=True
    )
    issue_description = models.TextField(blank=True)

    # Files & Media
    attachments = models.JSONField(default=list)
    problem_images = models.JSONField(default=list)

    # Management
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'is_staff': True}
    )

    # Response Tracking
    response_date = models.DateTimeField(null=True, blank=True)
    response_time = models.DurationField(null=True, blank=True)
    resolution_date = models.DateTimeField(null=True, blank=True)
    resolution_time = models.DurationField(null=True, blank=True)

    # Notes
    internal_notes = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)

    # Source Tracking
    source = models.CharField(
        max_length=50,
        choices=[
            ('website', 'Website Form'),
            ('email', 'Direct Email'),
            ('phone', 'Phone Call'),
            ('whatsapp', 'WhatsApp'),
            ('social', 'Social Media'),
            ('referral', 'Customer Referral')
        ],
        default='website'
    )
    referrer_url = models.URLField(blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['inquiry_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_inquiry_type_display()} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        # Calculate response time when first responded
        if self.response_date and not self.response_time:
            self.response_time = self.response_date - self.created_at

        # Calculate resolution time when resolved
        if self.resolution_date and not self.resolution_time:
            self.resolution_time = self.resolution_date - self.created_at

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('admin:content_contactsubmission_change', args=[self.pk])

    @property
    def is_overdue(self):
        """Check if response is overdue based on priority"""
        if self.status in [self.Status.RESOLVED, self.Status.CLOSED]:
            return False

        from django.utils import timezone
        from datetime import timedelta

        sla_times = {
            self.Priority.URGENT: timedelta(hours=2),
            self.Priority.HIGH: timedelta(hours=8),
            self.Priority.MEDIUM: timedelta(days=1),
            self.Priority.LOW: timedelta(days=3)
        }

        sla_time = sla_times.get(self.priority, timedelta(days=1))
        return timezone.now() - self.created_at > sla_time


class NewsletterSubscription(TimestampedModel):
    """Newsletter subscription model"""

    class Status(models.TextChoices):
        SUBSCRIBED = 'subscribed', 'Subscribed'
        UNSUBSCRIBED = 'unsubscribed', 'Unsubscribed'
        BOUNCED = 'bounced', 'Bounced'
        COMPLAINED = 'complained', 'Complained'

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBSCRIBED
    )

    # Subscription details
    subscription_date = models.DateTimeField(auto_now_add=True)
    unsubscription_date = models.DateTimeField(null=True, blank=True)
    confirmation_token = models.UUIDField(default=uuid.uuid4, editable=False)
    is_confirmed = models.BooleanField(default=False)

    # Preferences
    preferred_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
        ],
        default='weekly'
    )

    # Interests
    interests = models.JSONField(
        default=list,
        help_text="Topics of interest"
    )

    # Source tracking
    source = models.CharField(
        max_length=50,
        choices=[
            ('website', 'Website'),
            ('social', 'Social Media'),
            ('referral', 'Referral'),
            ('import', 'Import'),
            ('manual', 'Manual')
        ],
        default='website'
    )

    class Meta:
        ordering = ['-subscription_date']
        indexes = [
            models.Index(fields=['status', 'is_confirmed']),
        ]

    def __str__(self):
        return f"{self.email} - {self.get_status_display()}"

    def confirm_subscription(self):
        """Confirm newsletter subscription"""
        self.is_confirmed = True
        self.save(update_fields=['is_confirmed'])

    def unsubscribe(self):
        """Unsubscribe from newsletter"""
        from django.utils import timezone
        self.status = self.Status.UNSUBSCRIBED
        self.unsubscription_date = timezone.now()
        self.save(update_fields=['status', 'unsubscription_date'])


class BlogComment(TimestampedModel):
    """Comments for blog posts"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        SPAM = 'spam', 'Spam'
        REJECTED = 'rejected', 'Rejected'

    content_page = models.ForeignKey(
        ContentPage,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )

    # Commenter Info
    name = models.CharField(max_length=100)
    email = models.EmailField()
    website = models.URLField(blank=True)

    # Comment Content
    comment = models.TextField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Moderation
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_spam = models.BooleanField(default=False)

    # User relationship (if logged in)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['content_page', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.name} on {self.content_page.title}"

    def approve(self):
        """Approve comment"""
        self.status = self.Status.APPROVED
        self.save(update_fields=['status'])

        # Update comment count on content page
        self.content_page.comment_count = self.content_page.comments.filter(
            status=self.Status.APPROVED
        ).count()
        self.content_page.save(update_fields=['comment_count'])

    def mark_as_spam(self):
        """Mark comment as spam"""
        self.status = self.Status.SPAM
        self.is_spam = True
        self.save(update_fields=['status', 'is_spam'])


class ContentView(TimestampedModel):
    """Track content views for analytics"""
    content_page = models.ForeignKey(
        ContentPage,
        on_delete=models.CASCADE,
        related_name='content_views'
    )
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)

    # User info (if logged in)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # View duration tracking
    time_on_page = models.DurationField(null=True, blank=True)
    scroll_depth = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Percentage of page scrolled"
    )

    class Meta:
        indexes = [
            models.Index(fields=['content_page', 'created_at']),
            models.Index(fields=['ip_address', 'session_key']),
        ]

    def __str__(self):
        return f"View of {self.content_page.title} at {self.created_at}"


class ContentLike(TimestampedModel):
    """Track content likes"""
    content_page = models.ForeignKey(
        ContentPage,
        on_delete=models.CASCADE,
        related_name='content_likes'
    )
    ip_address = models.GenericIPAddressField()
    session_key = models.CharField(max_length=40, blank=True)

    # User info (if logged in)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = [
            ['content_page', 'ip_address'],
            ['content_page', 'user']
        ]
        indexes = [
            models.Index(fields=['content_page']),
        ]

    def __str__(self):
        return f"Like for {self.content_page.title}"


class ContentShare(TimestampedModel):
    """Track content shares"""

    class Platform(models.TextChoices):
        FACEBOOK = 'facebook', 'Facebook'
        TWITTER = 'twitter', 'Twitter'
        LINKEDIN = 'linkedin', 'LinkedIn'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        EMAIL = 'email', 'Email'
        COPY_LINK = 'copy_link', 'Copy Link'

    content_page = models.ForeignKey(
        ContentPage,
        on_delete=models.CASCADE,
        related_name='content_shares'
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices
    )
    ip_address = models.GenericIPAddressField()

    # User info (if logged in)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        indexes = [
            models.Index(fields=['content_page', 'platform']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Share of {self.content_page.title} on {self.get_platform_display()}"

# Content managers
class PublishedContentManager(models.Manager):
    """Manager for published content only"""

    def get_queryset(self):
        from django.utils import timezone
        return super().get_queryset().filter(
            status=ContentPage.Status.PUBLISHED,
            is_active=True,
            publish_date__lte=timezone.now()
        )


class FeaturedContentManager(models.Manager):
    """Manager for featured content"""

    def get_queryset(self):
        from django.utils import timezone
        return super().get_queryset().filter(
            status=ContentPage.Status.PUBLISHED,
            is_active=True,
            is_featured=True,
            publish_date__lte=timezone.now()
        ).filter(
            models.Q(featured_until__isnull=True) |
            models.Q(featured_until__gte=timezone.now())
        )


# Add managers to ContentPage model
ContentPage.add_to_class('published', PublishedContentManager())
ContentPage.add_to_class('featured', FeaturedContentManager())