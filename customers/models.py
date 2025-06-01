# apps/customers/models.py - Enhanced customer models
from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import timedelta
import uuid

from core.models import TimestampedModel, CacheableMixin
from core.utils import OrderNumberGenerator, NotificationService


class MembershipLevel(models.TextChoices):
    """Membership levels for loyalty program"""
    BRONZE = 'bronze', 'Bronze (0-1,999 pts)'
    SILVER = 'silver', 'Silver (2,000-4,999 pts)'
    GOLD = 'gold', 'Gold (5,000-9,999 pts)'
    PLATINUM = 'platinum', 'Platinum (10,000+ pts)'


class CustomerProfile(TimestampedModel, CacheableMixin):
    """Enhanced customer profile with advanced features"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    
    # Personal Information
    phone = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Additional Info
    occupation = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    
    # Loyalty Program
    total_points = models.PositiveIntegerField(default=0, db_index=True)
    lifetime_points = models.PositiveIntegerField(default=0)
    membership_level = models.CharField(
        max_length=20,
        choices=MembershipLevel.choices,
        default=MembershipLevel.BRONZE,
        db_index=True
    )
    membership_since = models.DateTimeField(default=timezone.now)
    
    # Customer Metrics
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_orders = models.PositiveIntegerField(default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    last_order_date = models.DateTimeField(null=True, blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    whatsapp_notifications = models.BooleanField(default=True)
    promotional_offers = models.BooleanField(default=True)
    newsletter_subscription = models.BooleanField(default=True)
    preferred_contact_method = models.CharField(
        max_length=10,
        choices=[
            ('email', 'Email'),
            ('whatsapp', 'WhatsApp'),
            ('phone', 'Phone'),
            ('sms', 'SMS')
        ],
        default='whatsapp'
    )
    
    # Account Settings
    is_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4, editable=False)
    two_factor_enabled = models.BooleanField(default=False)
    
    # Referral Program
    referral_code = models.CharField(max_length=20, unique=True, blank=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    total_referrals = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Customer Profile"
        verbose_name_plural = "Customer Profiles"
        indexes = [
            models.Index(fields=['membership_level', 'total_points']),
            models.Index(fields=['is_verified', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.get_membership_level_display()}"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        self.update_membership_level()
        super().save(*args, **kwargs)

    def generate_referral_code(self):
        """Generate unique referral code"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not CustomerProfile.objects.filter(referral_code=code).exists():
                return code

    def update_membership_level(self):
        """Update membership level based on total points"""
        old_level = self.membership_level
        
        if self.total_points >= 10000:
            new_level = MembershipLevel.PLATINUM
        elif self.total_points >= 5000:
            new_level = MembershipLevel.GOLD
        elif self.total_points >= 2000:
            new_level = MembershipLevel.SILVER
        else:
            new_level = MembershipLevel.BRONZE
        
        if old_level != new_level:
            self.membership_level = new_level
            self.membership_since = timezone.now()
            # Send level upgrade notification
            self.send_level_upgrade_notification(old_level, new_level)

    def add_points(self, points, reason="", order=None):
        """Add points to customer account with transaction record"""
        self.total_points += points
        self.lifetime_points += points
        
        # Create point transaction
        PointTransaction.objects.create(
            customer=self,
            points=points,
            transaction_type=PointTransaction.TransactionType.EARNED,
            reason=reason,
            order=order
        )
        
        self.update_membership_level()
        self.save(update_fields=['total_points', 'lifetime_points', 'membership_level'])

    def redeem_points(self, points, reason="", order=None):
        """Redeem points from customer account"""
        if self.total_points >= points:
            self.total_points -= points
            
            # Create point transaction
            PointTransaction.objects.create(
                customer=self,
                points=-points,
                transaction_type=PointTransaction.TransactionType.REDEEMED,
                reason=reason,
                order=order
            )
            
            self.save(update_fields=['total_points'])
            return True
        return False

    def get_discount_percentage(self):
        """Get discount percentage based on membership level"""
        discounts = {
            MembershipLevel.BRONZE: 0,
            MembershipLevel.SILVER: 5,
            MembershipLevel.GOLD: 10,
            MembershipLevel.PLATINUM: 15
        }
        return discounts.get(self.membership_level, 0)

    def get_points_to_next_level(self):
        """Calculate points needed for next membership level"""
        thresholds = {
            MembershipLevel.BRONZE: 2000,
            MembershipLevel.SILVER: 5000,
            MembershipLevel.GOLD: 10000,
            MembershipLevel.PLATINUM: None
        }
        
        next_threshold = thresholds.get(self.membership_level)
        if next_threshold is None:
            return 0  # Already at max level
        
        return max(0, next_threshold - self.total_points)

    def send_level_upgrade_notification(self, old_level, new_level):
        """Send notification when membership level is upgraded"""
        if self.email_notifications:
            NotificationService.send_email_notification(
                subject=f"Selamat! Anda naik ke {new_level.label}",
                template_name='emails/membership_upgrade.html',
                context={
                    'customer': self,
                    'old_level': old_level,
                    'new_level': new_level,
                    'discount_percentage': self.get_discount_percentage()
                },
                recipient_list=[self.user.email]
            )


class ServiceOrder(TimestampedModel):
    """Enhanced service order model with advanced tracking"""
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Menunggu Konfirmasi'
        CONFIRMED = 'confirmed', 'Dikonfirmasi'
        IN_PROGRESS = 'in_progress', 'Sedang Dikerjakan'
        WAITING_PARTS = 'waiting_parts', 'Menunggu Spare Part'
        TESTING = 'testing', 'Testing & Quality Check'
        COMPLETED = 'completed', 'Selesai'
        READY_PICKUP = 'ready_pickup', 'Siap Diambil'
        DELIVERED =