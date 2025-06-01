# core/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import BusinessInfo, Brand, DeviceModel


@admin.register(BusinessInfo)
class BusinessInfoAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'business_type', 'city', 'is_active', 'created_at']
    list_filter = ['business_type', 'is_active', 'city']
    search_fields = ['business_name', 'address', 'phone', 'email']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('business_name', 'business_type', 'is_active')
        }),
        ('Contact Information', {
            'fields': ('address', 'city', 'province', 'postal_code', 'phone', 'whatsapp', 'email', 'website')
        }),
        ('Business Hours', {
            'fields': ('opening_hours',)
        }),
        ('SEO & Social', {
            'fields': ('meta_description', 'social_media')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ['name', 'brand_type', 'is_supported', 'service_difficulty', 'spare_parts_availability',
                    'models_count']
    list_filter = ['brand_type', 'is_supported', 'service_difficulty', 'spare_parts_availability']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'brand_type', 'logo', 'description')
        }),
        ('Support Information', {
            'fields': ('is_supported', 'service_difficulty', 'spare_parts_availability', 'warranty_period')
        }),
        ('Contact Information', {
            'fields': ('website', 'support_email'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def models_count(self, obj):
        return obj.device_models.count()

    models_count.short_description = 'Device Models'


@admin.register(DeviceModel)
class DeviceModelAdmin(admin.ModelAdmin):
    list_display = ['brand', 'name', 'model_number', 'year_released', 'complexity_multiplier']
    list_filter = ['brand', 'year_released', 'storage_type']
    search_fields = ['name', 'model_number', 'brand__name']
    autocomplete_fields = ['brand']

    fieldsets = (
        ('Basic Information', {
            'fields': ('brand', 'name', 'model_number', 'year_released')
        }),
        ('Technical Specifications', {
            'fields': ('processor', 'ram_capacity', 'storage_type', 'screen_size')
        }),
        ('Service Information', {
            'fields': ('service_manual_url', 'common_issues', 'complexity_multiplier')
        }),
    )