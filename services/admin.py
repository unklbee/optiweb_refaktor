# services/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import ServiceCategory, Service, ServiceReview, ServiceFAQ


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'is_featured', 'show_in_menu', 'service_count', 'is_active']
    list_filter = ['is_featured', 'show_in_menu', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'icon', 'color')
        }),
        ('Display Settings', {
            'fields': ('order', 'is_featured', 'show_in_menu', 'is_active')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price_range', 'difficulty', 'is_featured', 'popularity_score',
                    'average_rating']
    list_filter = ['category', 'difficulty', 'is_featured', 'is_active', 'requires_appointment']
    search_fields = ['name', 'short_description', 'description']
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ['supported_brands', 'tags']
    readonly_fields = ['popularity_score', 'average_rating', 'total_orders']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'category', 'short_description')
        }),
        ('Content', {
            'fields': ('description', 'requirements', 'process_steps')
        }),
        ('Pricing & Service Details', {
            'fields': ('base_price_min', 'base_price_max', 'difficulty', 'estimated_duration', 'warranty_period')
        }),
        ('Availability', {
            'fields': ('requires_appointment', 'available_priorities', 'supported_brands')
        }),
        ('Media', {
            'fields': ('featured_image', 'gallery_images', 'tutorial_video_url')
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'target_keywords', 'tags'),
            'classes': ('collapse',)
        }),
        ('Display Settings', {
            'fields': ('is_featured', 'display_order', 'is_active')
        }),
        ('Statistics', {
            'fields': ('popularity_score', 'average_rating', 'total_orders'),
            'classes': ('collapse',)
        })
    )

    def price_range(self, obj):
        return obj.get_price_range()

    price_range.short_description = 'Price Range'


class ServiceFAQInline(admin.TabularInline):
    model = ServiceFAQ
    extra = 1


@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = ['service', 'customer_name', 'rating', 'is_verified', 'is_featured', 'is_public', 'created_at']
    list_filter = ['rating', 'is_verified', 'is_featured', 'is_public', 'created_at']
    search_fields = ['service__name', 'customer__user__first_name', 'customer__user__last_name', 'title', 'content']
    readonly_fields = ['helpful_count', 'not_helpful_count', 'helpfulness_ratio']

    def customer_name(self, obj):
        return obj.customer.user.get_full_name()

    customer_name.short_description = 'Customer'
