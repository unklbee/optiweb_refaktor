# apps/api/serializers.py - DRF Serializers
from rest_framework import serializers
from rest_framework.reverse import reverse
from django.contrib.auth.models import User
from apps.core.models import BusinessInfo, Brand
from apps.services.models import Service, ServiceCategory, ServiceReview
from apps.customers.models import CustomerProfile, ServiceOrder, PointTransaction
from apps.content.models import ContentPage, FAQ, Testimonial


class BusinessInfoSerializer(serializers.ModelSerializer):
    """Serializer for business information"""
    social_media_links = serializers.SerializerMethodField()

    class Meta:
        model = BusinessInfo
        fields = [
            'business_name', 'business_type', 'address', 'city', 'province',
            'phone', 'whatsapp', 'email', 'website', 'opening_hours',
            'social_media_links', 'latitude', 'longitude'
        ]

    def get_social_media_links(self, obj):
        return obj.social_media or {}


class BrandSerializer(serializers.ModelSerializer):
    """Serializer for laptop brands"""
    logo_url = serializers.SerializerMethodField()
    service_models_count = serializers.ReadOnlyField()

    class Meta:
        model = Brand
        fields = [
            'id', 'name', 'slug', 'logo_url', 'brand_type', 'description',
            'is_supported', 'service_difficulty', 'spare_parts_availability',
            'service_models_count'
        ]

    def get_logo_url(self, obj):
        if obj.logo:
            return self.context['request'].build_absolute_uri(obj.logo.url)
        return None


class ServiceCategorySerializer(serializers.ModelSerializer):
    """Serializer for service categories"""
    services_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'color',
            'order', 'services_count'
        ]

    def get_services_count(self, obj):
        return obj.active_services_count


class ServiceListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for service listings"""
    category = ServiceCategorySerializer(read_only=True)
    price_range = serializers.SerializerMethodField()
    featured_image_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'slug', 'category', 'short_description',
            'price_range', 'difficulty', 'estimated_duration',
            'featured_image_url', 'is_featured', 'popularity_score',
            'average_rating', 'total_orders', 'url'
        ]

    def get_price_range(self, obj):
        return obj.get_price_range()

    def get_featured_image_url(self, obj):
        if obj.featured_image:
            return self.context['request'].build_absolute_uri(obj.featured_image.url)
        return None

    def get_url(self, obj):
        return reverse('api:service-detail', kwargs={'slug': obj.slug},
                       request=self.context['request'])


class ServiceDetailSerializer(ServiceListSerializer):
    """Detailed serializer for service details"""
    supported_brands = BrandSerializer(many=True, read_only=True)
    tags = serializers.StringRelatedField(many=True, read_only=True)
    reviews_summary = serializers.SerializerMethodField()
    process_steps = serializers.JSONField(read_only=True)

    class Meta(ServiceListSerializer.Meta):
        fields = ServiceListSerializer.Meta.fields + [
            'description', 'requirements', 'process_steps',
            'warranty_period', 'requires_appointment', 'available_priorities',
            'supported_brands', 'gallery_images', 'tutorial_video_url',
            'tags', 'reviews_summary'
        ]

    def get_reviews_summary(self, obj):
        reviews = obj.reviews.filter(is_public=True)
        if not reviews.exists():
            return None

        from django.db.models import Avg, Count
        stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id')
        )

        return {
            'average_rating': round(stats['avg_rating'], 1) if stats['avg_rating'] else 0,
            'total_reviews': stats['total_reviews'],
            'rating_distribution': self.get_rating_distribution(reviews)
        }

    def get_rating_distribution(self, reviews):
        distribution = {}
        for i in range(1, 6):
            count = reviews.filter(rating=i).count()
            distribution[str(i)] = count
        return distribution


class ServiceReviewSerializer(serializers.ModelSerializer):
    """Serializer for service reviews"""
    customer_name = serializers.CharField(source='customer.user.get_full_name', read_only=True)
    customer_avatar = serializers.SerializerMethodField()
    helpful_ratio = serializers.ReadOnlyField()

    class Meta:
        model = ServiceReview
        fields = [
            'id', 'rating', 'title', 'content', 'customer_name',
            'customer_avatar', 'created_at', 'helpful_count',
            'not_helpful_count', 'helpful_ratio', 'images'
        ]

    def get_customer_avatar(self, obj):
        if hasattr(obj.customer, 'avatar') and obj.customer.avatar:
            return self.context['request'].build_absolute_uri(obj.customer.avatar.url)