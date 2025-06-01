# ================================
# CORE MODELS & UTILITIES REFACTORING
# ================================

# apps/core/models.py - Base models and core entities
from django.db import models
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User
from django.core.validators import EmailValidator, RegexValidator
import uuid
from datetime import datetime, timedelta


class TimestampedModel(models.Model):
    """Base model with timestamp fields and common methods"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def soft_delete(self):
        """Soft delete by setting is_active to False"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def restore(self):
        """Restore soft deleted object"""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])


class CacheableMixin:
    """Mixin for models that need caching functionality"""
    CACHE_TIMEOUT = 3600  # 1 hour default

    @classmethod
    def get_cache_key(cls, **kwargs):
        """Generate cache key for model instances"""
        key_parts = [cls.__name__.lower()]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}_{v}")
        return ":".join(key_parts)

    def invalidate_cache(self):
        """Invalidate related cache entries"""
        cache_pattern = f"{self.__class__.__name__.lower()}:*"
        # Implementation depends on cache backend
        pass


class AuditMixin(models.Model):
    """Mixin for audit trails"""
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_created'
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='%(class)s_updated'
    )

    class Meta:
        abstract = True


class BusinessInfo(TimestampedModel, CacheableMixin):
    """Enhanced business information model"""
    business_name = models.CharField(max_length=255, verbose_name=_("Business Name"))
    business_type = models.CharField(
        max_length=50,
        choices=[
            ('service_center', _('Service Center')),
            ('repair_shop', _('Repair Shop')),
            ('retail', _('Retail Store'))
        ],
        default='service_center'
    )

    # Contact Information
    address = models.TextField(verbose_name=_("Address"))
    city = models.CharField(max_length=100, default='Bandung')
    province = models.CharField(max_length=100, default='Jawa Barat')
    postal_code = models.CharField(max_length=10, blank=True)

    # Communication
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(r'^[0-9\-\+\(\)\s]+$', 'Enter valid phone number')]
    )
    whatsapp = models.CharField(max_length=20)
    email = models.EmailField(validators=[EmailValidator()])
    website = models.URLField(blank=True)

    # Business Hours
    opening_hours = models.JSONField(default=dict, help_text="Store opening hours")

    # SEO & Social
    meta_description = models.TextField(max_length=160, blank=True)
    social_media = models.JSONField(default=dict, help_text="Social media links")

    # Geolocation
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        verbose_name = _("Business Information")
        verbose_name_plural = _("Business Information")

    def __str__(self):
        return self.business_name

    @classmethod
    def get_cached_info(cls):
        """Get cached business info"""
        cache_key = cls.get_cache_key()
        business_info = cache.get(cache_key)

        if business_info is None:
            try:
                business_info = cls.objects.filter(is_active=True).first()
                if business_info:
                    cache.set(cache_key, business_info, cls.CACHE_TIMEOUT)
            except cls.DoesNotExist:
                business_info = None

        return business_info

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.invalidate_cache()


class Brand(TimestampedModel):
    """Enhanced brand model with better categorization"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    brand_type = models.CharField(
        max_length=20,
        choices=[
            ('laptop', _('Laptop')),
            ('smartphone', _('Smartphone')),
            ('tablet', _('Tablet')),
            ('accessory', _('Accessory'))
        ],
        default='laptop'
    )

    # Brand Information
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    support_email = models.EmailField(blank=True)
    warranty_period = models.PositiveIntegerField(default=12, help_text="Months")

    # Service Support
    is_supported = models.BooleanField(default=True, db_index=True)
    service_difficulty = models.CharField(
        max_length=10,
        choices=[
            ('easy', _('Easy')),
            ('medium', _('Medium')),
            ('hard', _('Hard')),
            ('expert', _('Expert Only'))
        ],
        default='medium'
    )

    # Spare Parts
    spare_parts_availability = models.CharField(
        max_length=10,
        choices=[
            ('excellent', _('Excellent')),
            ('good', _('Good')),
            ('limited', _('Limited')),
            ('rare', _('Rare'))
        ],
        default='good'
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['brand_type', 'is_supported']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_brand_type_display()})"

    @property
    def service_models_count(self):
        """Count of service models for this brand"""
        return self.device_models.filter(is_active=True).count()


class DeviceModel(TimestampedModel):
    """Device models for each brand"""
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='device_models')
    name = models.CharField(max_length=100)
    model_number = models.CharField(max_length=50, blank=True)
    year_released = models.PositiveIntegerField(null=True, blank=True)

    # Technical Specifications
    processor = models.CharField(max_length=100, blank=True)
    ram_capacity = models.CharField(max_length=50, blank=True)
    storage_type = models.CharField(max_length=20, blank=True)
    screen_size = models.CharField(max_length=20, blank=True)

    # Service Information
    service_manual_url = models.URLField(blank=True)
    common_issues = models.JSONField(default=list, help_text="List of common issues")

    # Pricing Factors
    complexity_multiplier = models.DecimalField(
        max_digits=3, decimal_places=2, default=1.00,
        help_text="Pricing multiplier based on complexity"
    )

    class Meta:
        unique_together = ['brand', 'name']
        ordering = ['brand__name', 'name']

    def __str__(self):
        return f"{self.brand.name} {self.name}"