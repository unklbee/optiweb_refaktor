# customers/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CustomerProfile, ServiceOrder, OrderStatusHistory, PointTransaction,
    LoyaltyReward, RewardRedemption, CustomerNotification, CustomerDevice
)


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'membership_level', 'total_points', 'total_orders', 'total_spent', 'is_verified']
    list_filter = ['membership_level', 'is_verified', 'promotional_offers', 'newsletter_subscription']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'phone', 'referral_code']
    readonly_fields = ['total_points', 'lifetime_points', 'total_orders', 'average_order_value', 'referral_code',
                       'total_referrals']

    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Information', {
            'fields': ('phone', 'whatsapp', 'address', 'city', 'postal_code', 'birth_date', 'gender', 'avatar')
        }),
        ('Additional Info', {
            'fields': ('occupation', 'company', 'emergency_contact', 'emergency_phone'),
            'classes': ('collapse',)
        }),
        ('Loyalty Program', {
            'fields': ('total_points', 'lifetime_points', 'membership_level', 'membership_since')
        }),
        ('Customer Metrics', {
            'fields': ('total_spent', 'total_orders', 'average_order_value', 'last_order_date'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': ('email_notifications', 'whatsapp_notifications', 'promotional_offers', 'newsletter_subscription',
                       'preferred_contact_method')
        }),
        ('Account Settings', {
            'fields': ('is_verified', 'two_factor_enabled'),
            'classes': ('collapse',)
        }),
        ('Referral Program', {
            'fields': ('referral_code', 'referred_by', 'total_referrals'),
            'classes': ('collapse',)
        })
    )

    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    user_name.short_description = 'Customer Name'


class OrderStatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ['created_at']


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'service', 'status', 'priority', 'estimated_cost', 'created_at']
    list_filter = ['status', 'priority', 'service__category', 'assigned_technician', 'created_at']
    search_fields = ['order_number', 'customer__user__first_name', 'customer__user__last_name', 'device_model',
                     'problem_description']
    readonly_fields = ['order_number', 'created_at', 'updated_at']
    autocomplete_fields = ['customer', 'service', 'device_brand', 'assigned_technician']
    inlines = [OrderStatusHistoryInline]

    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'customer', 'service', 'status', 'priority')
        }),
        ('Device Information', {
            'fields': ('device_brand', 'device_model', 'device_serial', 'device_condition')
        }),
        ('Problem Description', {
            'fields': ('problem_description', 'problem_images')
        }),
        ('Pricing', {
            'fields': ('estimated_cost', 'final_cost', 'parts_cost', 'labor_cost', 'discount_amount', 'points_used',
                       'points_earned')
        }),
        ('Timeline', {
            'fields': ('estimated_completion', 'actual_completion', 'pickup_date', 'delivery_date')
        }),
        ('Assignment & Notes', {
            'fields': ('assigned_technician', 'technician_notes', 'internal_notes', 'customer_notes')
        }),
        ('Quality Assurance', {
            'fields': ('qa_checked', 'qa_notes', 'qa_checklist'),
            'classes': ('collapse',)
        }),
        ('Warranty', {
            'fields': ('warranty_expires', 'warranty_terms'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def customer_name(self, obj):
        return obj.customer.user.get_full_name()

    customer_name.short_description = 'Customer'

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.status in ['completed', 'delivered', 'cancelled']:
            readonly.extend(['customer', 'service', 'priority'])
        return readonly


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'points', 'transaction_type', 'reason', 'balance_after', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['customer__user__first_name', 'customer__user__last_name', 'reason']
    readonly_fields = ['balance_before', 'balance_after', 'created_at']

    def customer_name(self, obj):
        return obj.customer.user.get_full_name()

    customer_name.short_description = 'Customer'


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'reward_type', 'points_required', 'is_available', 'current_redemptions', 'max_redemptions']
    list_filter = ['reward_type', 'is_available', 'minimum_membership_level']
    search_fields = ['name', 'description']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'reward_type', 'points_required')
        }),
        ('Reward Value', {
            'fields': ('discount_percentage', 'discount_amount', 'free_service')
        }),
        ('Availability', {
            'fields': ('is_available', 'available_from', 'available_until', 'max_redemptions', 'current_redemptions')
        }),
        ('Restrictions', {
            'fields': ('minimum_membership_level', 'minimum_order_value')
        }),
        ('Media', {
            'fields': ('image',)
        })
    )


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'reward', 'status', 'voucher_code', 'used_at', 'expires_at']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['customer__user__first_name', 'customer__user__last_name', 'voucher_code']
    readonly_fields = ['voucher_code', 'created_at']

    def customer_name(self, obj):
        return obj.customer.user.get_full_name()

    customer_name.short_description = 'Customer'


@admin.register(CustomerNotification)
class CustomerNotificationAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['customer__user__first_name', 'customer__user__last_name', 'title', 'message']
    readonly_fields = ['read_at', 'created_at']

    def customer_name(self, obj):
        return obj.customer.user.get_full_name()

    customer_name.short_description = 'Customer'


@admin.register(CustomerDevice)
class CustomerDeviceAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'brand', 'model', 'purchase_date', 'service_count', 'last_service_date']
    list_filter = ['brand', 'purchase_date', 'last_service_date']
    search_fields = ['customer__user__first_name', 'customer__user__last_name', 'model', 'serial_number']

    def customer_name(self, obj):
        return obj.customer.user.get_full_name()

    customer_name.short_description = 'Customer'
