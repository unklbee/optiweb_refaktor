# Content Managers
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


# Add managers to models
ContentPage.add_to_class('published', PublishedContentManager())
ContentPage.add_to_class('featured', FeaturedContentManager())