# apps/content/models.py - Enhanced content management
from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from ckeditor.fields import RichTextField
from taggit.managers import TaggableManager
from meta.models import ModelMeta
from apps.core.models import TimestampedModel, CacheableMixin
from apps.core.utils import SEOHelper
from decimal import Decimal


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
    problem_description = models.TextField(blank=True)
    
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

