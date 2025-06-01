# content/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    ContentCategory, ContentPage, FAQ, Testimonial, ContactSubmission,
    NewsletterSubscription, BlogComment
)


@admin.register(ContentCategory)
class ContentCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'order', 'is_active']
    list_filter = ['parent', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(ContentPage)
class ContentPageAdmin(admin.ModelAdmin):
    list_display = ['title', 'page_type', 'status', 'author', 'is_featured', 'view_count', 'publish_date']
    list_filter = ['page_type', 'status', 'is_featured', 'author', 'created_at']
    search_fields = ['title', 'content', 'meta_title']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['tags', 'related_pages', 'related_services', 'co_authors']
    readonly_fields = ['view_count', 'like_count', 'share_count', 'comment_count', 'reading_time']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'page_type', 'category', 'status')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'table_of_contents')
        }),
        ('Media', {
            'fields': ('featured_image', 'featured_image_alt', 'gallery_images')
        }),
        ('Authoring', {
            'fields': ('author', 'co_authors')
        }),
        ('Publishing', {
            'fields': ('publish_date', 'featured_until')
        }),
        ('SEO & Marketing', {
            'fields': ('meta_title', 'meta_description', 'target_keyword', 'secondary_keywords', 'focus_keyphrase'),
            'classes': ('collapse',)
        }),
        ('Social Media', {
            'fields': ('social_title', 'social_description', 'social_image'),
            'classes': ('collapse',)
        }),
        ('Display Settings', {
            'fields': ('is_featured', 'show_in_menu', 'menu_order', 'template_name')
        }),
        ('Analytics & Engagement', {
            'fields': ('view_count', 'like_count', 'share_count', 'comment_count', 'reading_time'),
            'classes': ('collapse',)
        }),
        ('Content Settings', {
            'fields': ('allow_comments', 'password_protected', 'password'),
            'classes': ('collapse',)
        }),
        ('Related Content', {
            'fields': ('related_pages', 'related_services', 'tags'),
            'classes': ('collapse',)
        })
    )

    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'category', 'order_priority', 'is_featured', 'view_count', 'helpfulness_ratio']
    list_filter = ['category', 'is_featured', 'is_active']
    search_fields = ['question', 'answer']
    prepopulated_fields = {'slug': ('question',)}
    filter_horizontal = ['related_services', 'related_faqs']
    ordering = ['category', 'order_priority']

    def question_short(self, obj):
        return obj.question[:50] + '...' if len(obj.question) > 50 else obj.question

    question_short.short_description = 'Question'


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'rating', 'service_type', 'is_verified', 'is_featured', 'is_public', 'created_at']
    list_filter = ['rating', 'service_type', 'is_verified', 'is_featured', 'is_public', 'laptop_brand']
    search_fields = ['customer_name', 'review_text', 'title']
    prepopulated_fields = {'slug': ('customer_name', 'rating')}
    readonly_fields = ['helpful_count', 'view_count', 'star_percentage']

    fieldsets = (
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_photo', 'customer_location', 'customer_occupation')
        }),
        ('Device & Service Information', {
            'fields': ('laptop_brand', 'laptop_model', 'service_type', 'service_date')
        }),
        ('Review Content', {
            'fields': ('rating', 'title', 'review_text', 'pros', 'cons')
        }),
        ('Media', {
            'fields': ('before_images', 'after_images', 'video_url'),
            'classes': ('collapse',)
        }),
        ('Verification & Moderation', {
            'fields': ('is_verified', 'verification_method', 'is_featured', 'is_public')
        }),
        ('SEO', {
            'fields': ('slug',),
            'classes': ('collapse',)
        }),
        ('Analytics', {
            'fields': ('helpful_count', 'view_count', 'star_percentage'),
            'classes': ('collapse',)
        }),
        ('Related Order', {
            'fields': ('order',),
            'classes': ('collapse',)
        })
    )


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'inquiry_type', 'status', 'priority', 'assigned_to', 'is_overdue', 'created_at']
    list_filter = ['inquiry_type', 'status', 'priority', 'assigned_to', 'source', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['response_time', 'resolution_time', 'ip_address', 'user_agent']

    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone', 'company')
        }),
        ('Inquiry Details', {
            'fields': ('inquiry_type', 'subject', 'message')
        }),
        ('Device Information', {
            'fields': ('laptop_brand', 'laptop_model', 'device_age', 'issue_description'),
            'classes': ('collapse',)
        }),
        ('Files & Media', {
            'fields': ('attachments', 'problem_images'),
            'classes': ('collapse',)
        }),
        ('Management', {
            'fields': ('status', 'priority', 'assigned_to')
        }),
        ('Response Tracking', {
            'fields': ('response_date', 'response_time', 'resolution_date', 'resolution_time'),
            'classes': ('collapse',)
        }),
        ('Notes', {
            'fields': ('internal_notes', 'customer_notes')
        }),
        ('Source Tracking', {
            'fields': ('source', 'referrer_url', 'user_agent', 'ip_address'),
            'classes': ('collapse',)
        }),
        ('Follow-up', {
            'fields': ('follow_up_required', 'follow_up_date', 'follow_up_notes'),
            'classes': ('collapse',)
        })
    )

    def is_overdue(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color: red;">Yes</span>')
        return format_html('<span style="color: green;">No</span>')

    is_overdue.short_description = 'Overdue'


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'status', 'is_confirmed', 'preferred_frequency', 'subscription_date']
    list_filter = ['status', 'is_confirmed', 'preferred_frequency', 'source', 'subscription_date']
    search_fields = ['email', 'name']
    readonly_fields = ['confirmation_token', 'subscription_date', 'unsubscription_date']

    actions = ['confirm_subscriptions', 'unsubscribe_selected']

    def confirm_subscriptions(self, request, queryset):
        updated = queryset.update(is_confirmed=True)
        self.message_user(request, f'{updated} subscriptions confirmed.')

    confirm_subscriptions.short_description = "Confirm selected subscriptions"

    def unsubscribe_selected(self, request, queryset):
        for subscription in queryset:
            subscription.unsubscribe()
        self.message_user(request, f'{queryset.count()} subscriptions unsubscribed.')

    unsubscribe_selected.short_description = "Unsubscribe selected"


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ['content_page', 'name', 'status', 'is_spam', 'created_at']
    list_filter = ['status', 'is_spam', 'content_page__page_type', 'created_at']
    search_fields = ['name', 'email', 'comment', 'content_page__title']
    readonly_fields = ['ip_address', 'user_agent', 'created_at']

    actions = ['approve_comments', 'mark_as_spam']

    def approve_comments(self, request, queryset):
        for comment in queryset:
            comment.approve()
        self.message_user(request, f'{queryset.count()} comments approved.')

    approve_comments.short_description = "Approve selected comments"

    def mark_as_spam(self, request, queryset):
        for comment in queryset:
            comment.mark_as_spam()
        self.message_user(request, f'{queryset.count()} comments marked as spam.')

    mark_as_spam.short_description = "Mark selected as spam"


# Customize Django admin
admin.site.site_header = "Service Laptop Bandung Admin"
admin.site.site_title = "SLB Admin"
admin.site.index_title = "Welcome to Service Laptop Bandung Administration"