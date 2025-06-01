# ================================
# SERVICES APP REFACTORING
# ================================

# apps/services/models.py - Enhanced service models
from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from ckeditor.fields import RichTextField
from meta.models import ModelMeta
from taggit.managers import TaggableManager
from apps.core.models import TimestampedModel, CacheableMixin, Brand
from apps.core.utils import SEOHelper, PriceCalculator
from decimal import Decimal
import uuid


class ServiceCategory(TimestampedModel, CacheableMixin):
    """Enhanced service category model"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=255, blank=True, help_text="CSS class or icon name")
    color = models.CharField(max_length=7, default="#3B82F6", help_text="Hex color code")

    # SEO fields
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(max_length=160, blank=True)

    # Display settings
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_featured = models.BooleanField(default=False)
    show_in_menu = models.BooleanField(default=True)

    # Statistics
    service_count = models.PositiveIntegerField(default=0, help_text="Number of services in category")
    average_completion_time = models.DurationField(null=True, blank=True)

    class Meta:
        verbose_name = "Service Category"
        verbose_name_plural = "Service Categories"
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'show_in_menu']),
            models.Index(fields=['order']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.meta_title:
            self.meta_title = f"Layanan {self.name} - Service Laptop Bandung"
        if not self.meta_description:
            self.meta_description = f"Layanan {self.name} terpercaya di Bandung dengan teknisi berpengalaman dan garansi resmi."
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('services:category', kwargs={'slug': self.slug})

    @property
    def active_services_count(self):
        return self.services.filter(is_active=True).count()


class ServiceDifficulty(models.TextChoices):
    """Service difficulty levels"""
    EASY = 'easy', 'Easy (1-2 hours)'
    MEDIUM = 'medium', 'Medium (3-6 hours)'
    HARD = 'hard', 'Hard (1-2 days)'
    EXPERT = 'expert', 'Expert (3+ days)'


class ServicePriority(models.TextChoices):
    """Service priority levels"""
    STANDARD = 'standard', 'Standard'
    EXPRESS = 'express', 'Express (+50%)'
    EMERGENCY = 'emergency', 'Emergency (+100%)'


class Service(TimestampedModel, ModelMeta, CacheableMixin):
    """Enhanced service model with advanced features"""

    # Basic Information
    name = models.CharField(max_length=255, help_text="Service name")
    slug = models.SlugField(unique=True, blank=True)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='services',
        null=True, blank=True
    )

    # Content
    short_description = models.CharField(max_length=500)
    description = RichTextField(help_text="Detailed service description")
    requirements = RichTextField(blank=True, help_text="What customer needs to bring")
    process_steps = models.JSONField(default=list, help_text="Service process steps")

    # Pricing
    base_price_min = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    base_price_max = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    # Service Details
    difficulty = models.CharField(
        max_length=10,
        choices=ServiceDifficulty.choices,
        default=ServiceDifficulty.MEDIUM
    )
    estimated_duration = models.DurationField(help_text="Estimated completion time")
    warranty_period = models.PositiveIntegerField(default=30, help_text="Warranty in days")

    # Availability
    requires_appointment = models.BooleanField(default=False)
    available_priorities = models.JSONField(
        default=list,
        help_text="Available priority levels for this service"
    )
    supported_brands = models.ManyToManyField(
        Brand,
        blank=True,
        help_text="Brands supported for this service"
    )

    # Media
    featured_image = models.ImageField(upload_to='services/', blank=True, null=True)
    gallery_images = models.JSONField(default=list, help_text="Additional service images")
    tutorial_video_url = models.URLField(blank=True)

    # SEO & Marketing
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(max_length=160, blank=True)
    target_keywords = models.TextField(blank=True, help_text="Comma-separated keywords")

    # Display Settings
    is_featured = models.BooleanField(default=False, db_index=True)
    display_order = models.PositiveIntegerField(default=0)

    # Statistics
    popularity_score = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(
        max_digits=3, decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('5.00'))]
    )
    total_orders = models.PositiveIntegerField(default=0)

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
        ordering = ['-is_featured', 'display_order', 'name']
        indexes = [
            models.Index(fields=['is_active', 'is_featured']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['popularity_score']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('services:detail', kwargs={'slug': self.slug})

    # Price calculation methods
    def get_price_range(self, brand=None, priority='standard', member_discount=0):
        """Calculate price range with modifiers"""
        brand_multiplier = self.get_brand_multiplier(brand)
        priority_multiplier = self.get_priority_multiplier(priority)

        min_price = PriceCalculator.calculate_service_price(
            self.base_price_min, brand_multiplier, 1.0, priority_multiplier, member_discount
        )
        max_price = PriceCalculator.calculate_service_price(
            self.base_price_max, brand_multiplier, 1.0, priority_multiplier, member_discount
        )

        if min_price == max_price:
            return f"Rp {min_price:,.0f}"
        return f"Rp {min_price:,.0f} - {max_price:,.0f}"

    def get_brand_multiplier(self, brand):
        """Get price multiplier based on brand difficulty"""
        if not brand:
            return 1.0

        multipliers = {
            'easy': 1.0,
            'medium': 1.1,
            'hard': 1.3,
            'expert': 1.5
        }
        return multipliers.get(brand.service_difficulty, 1.0)

    def get_priority_multiplier(self, priority):
        """Get price multiplier based on priority"""
        multipliers = {
            'standard': 1.0,
            'express': 1.5,
            'emergency': 2.0
        }
        return multipliers.get(priority, 1.0)

    # SEO methods
    def get_meta_title(self):
        if self.meta_title:
            return self.meta_title
        return SEOHelper.generate_meta_title(self.name)

    def get_meta_description(self):
        if self.meta_description:
            return self.meta_description
        return SEOHelper.generate_meta_description(self.short_description)

    def get_meta_keywords(self):
        keywords = ['service laptop bandung', 'reparasi laptop bandung']
        if self.target_keywords:
            keywords.extend([kw.strip() for kw in self.target_keywords.split(',')])
        keywords.extend([tag.name for tag in self.tags.all()])
        return keywords

    def get_meta_image(self):
        return self.featured_image.url if self.featured_image else None

    # Utility methods
    def is_supported_for_brand(self, brand):
        """Check if service supports specific brand"""
        if not self.supported_brands.exists():
            return True  # Support all brands if none specified
        return self.supported_brands.filter(id=brand.id).exists()

    def get_estimated_completion(self, priority='standard'):
        """Get estimated completion time based on priority"""
        from datetime import timedelta
        base_duration = self.estimated_duration

        if priority == 'express':
            return base_duration * 0.7  # 30% faster
        elif priority == 'emergency':
            return base_duration * 0.5  # 50% faster

        return base_duration

    def increment_popularity(self):
        """Increment popularity score"""
        self.popularity_score += 1
        self.save(update_fields=['popularity_score'])


class ServiceReview(TimestampedModel):
    """Customer reviews for services"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey('customers.CustomerProfile', on_delete=models.CASCADE)
    order = models.OneToOneField(
        'customers.ServiceOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    # Review Content
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField(max_length=200)
    content = models.TextField()

    # Media
    images = models.JSONField(default=list, help_text="Review images")

    # Moderation
    is_verified = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)

    # Helpfulness
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['service', 'customer']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.service.name} - {self.rating}★ by {self.customer.user.get_full_name()}"

    @property
    def helpfulness_ratio(self):
        total = self.helpful_count + self.not_helpful_count
        return (self.helpful_count / total * 100) if total > 0 else 0


class ServiceFAQ(TimestampedModel):
    """Frequently asked questions for services"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = RichTextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return f"{self.service.name} - {self.question[:50]}"
