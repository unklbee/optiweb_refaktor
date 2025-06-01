# apps/services/managers.py - Custom managers
class ServiceManager(models.Manager):
    """Custom manager for Service model"""

    def active(self):
        return self.filter(is_active=True)

    def featured(self):
        return self.active().filter(is_featured=True)

    def by_category(self, category_slug):
        return self.active().filter(category__slug=category_slug)

    def popular(self, limit=10):
        return self.active().order_by('-popularity_score')[:limit]

    def for_brand(self, brand):
        return self.active().filter(
            models.Q(supported_brands__isnull=True) |
            models.Q(supported_brands=brand)
        ).distinct()


# Add manager to Service model
Service.add_to_class('objects', ServiceManager())
