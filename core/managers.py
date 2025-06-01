# apps/core/managers.py - Custom managers
from django.db import models
from django.utils import timezone


class ActiveManager(models.Manager):
    """Manager for active objects only"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class BusinessInfoManager(models.Manager):
    """Custom manager for BusinessInfo"""
    def get_main_info(self):
        """Get the main business info (cached)"""
        return BusinessInfo.get_cached_info()