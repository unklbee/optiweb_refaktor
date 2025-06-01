# customers/models.py - Enhanced customer models
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
    city = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=10, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', 'Laki-laki'),
            ('female', 'Perempuan'),
        ],
        blank=True
    )
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

    def process_referral(self, new_customer):
        """Process referral when new customer registers"""
        # Add points to referrer
        self.add_points(100, f"Referral bonus for {new_customer.user.get_full_name()}")

        # Add points to new customer
        new_customer.referred_by = self
        new_customer.add_points(50, "New customer referral bonus")

        # Increment referral count
        self.total_referrals += 1
        self.save(update_fields=['total_referrals'])


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
        DELIVERED = 'delivered', 'Sudah Diambil'
        CANCELLED = 'cancelled', 'Dibatalkan'
        REFUNDED = 'refunded', 'Dikembalikan'

    class Priority(models.TextChoices):
        STANDARD = 'standard', 'Standard (3-5 hari)'
        EXPRESS = 'express', 'Express (1-2 hari)'
        EMERGENCY = 'emergency', 'Emergency (Same day)'

    # Order Information
    order_number = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='orders')
    service = models.ForeignKey('services.Service', on_delete=models.CASCADE)

    # Device Information
    device_brand = models.ForeignKey(
        'core.Brand',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    device_model = models.CharField(max_length=100)
    device_serial = models.CharField(max_length=100, blank=True)
    device_condition = models.TextField(help_text="Physical condition of device")

    # Problem Description
    problem_description = models.TextField()
    problem_images = models.JSONField(default=list, help_text="Images of the problem")

    # Service Details
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.STANDARD
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True
    )

    # Pricing
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    parts_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Discounts & Points
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    points_used = models.PositiveIntegerField(default=0)
    points_earned = models.PositiveIntegerField(default=0)

    # Timeline
    estimated_completion = models.DateTimeField(null=True, blank=True)
    actual_completion = models.DateTimeField(null=True, blank=True)
    pickup_date = models.DateTimeField(null=True, blank=True)
    delivery_date = models.DateTimeField(null=True, blank=True)

    # Assignment
    assigned_technician = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'groups__name': 'Technicians'}
    )

    # Internal Notes
    technician_notes = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)
    customer_notes = models.TextField(blank=True)

    # Quality Assurance
    qa_checked = models.BooleanField(default=False)
    qa_notes = models.TextField(blank=True)
    qa_checklist = models.JSONField(default=dict)

    # Warranty
    warranty_expires = models.DateField(null=True, blank=True)
    warranty_terms = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['order_number']),
            models.Index(fields=['status', 'priority']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.customer.user.get_full_name()} - {self.get_status_display()}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = OrderNumberGenerator.generate()

        # Calculate estimated completion based on priority
        if not self.estimated_completion and self.service:
            self.estimated_completion = self.calculate_estimated_completion()

        # Set warranty expiration
        if self.status == self.Status.COMPLETED and not self.warranty_expires:
            self.warranty_expires = timezone.now().date() + timedelta(days=self.service.warranty_period)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('customers:order_detail', kwargs={'order_number': self.order_number})

    def calculate_estimated_completion(self):
        """Calculate estimated completion time based on service and priority"""
        if not self.service:
            return None

        base_duration = self.service.estimated_duration

        # Adjust based on priority
        if self.priority == self.Priority.EXPRESS:
            base_duration = base_duration * 0.7
        elif self.priority == self.Priority.EMERGENCY:
            base_duration = base_duration * 0.5

        return timezone.now() + base_duration

    def get_total_cost(self):
        """Calculate total cost including parts and labor"""
        if self.final_cost:
            return self.final_cost
        elif self.estimated_cost:
            return self.estimated_cost
        else:
            return self.parts_cost + self.labor_cost

    def get_discounted_total(self):
        """Get total cost after discount"""
        total = self.get_total_cost()
        return total - self.discount_amount

    def can_be_cancelled(self):
        """Check if order can be cancelled"""
        return self.status in [self.Status.DRAFT, self.Status.PENDING, self.Status.CONFIRMED]

    def update_status(self, new_status, notes="", user=None):
        """Update order status with logging"""
        old_status = self.status
        self.status = new_status

        # Create status history
        OrderStatusHistory.objects.create(
            order=self,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
            changed_by=user
        )

        # Send notification to customer
        if self.customer.email_notifications:
            self.send_status_notification()

        self.save(update_fields=['status'])

    def send_status_notification(self):
        """Send status update notification to customer"""
        NotificationService.send_email_notification(
            subject=f"Update Order #{self.order_number}",
            template_name='emails/order_status_update.html',
            context={
                'order': self,
                'customer': self.customer,
                'status_display': self.get_status_display()
            },
            recipient_list=[self.customer.user.email]
        )


class OrderStatusHistory(TimestampedModel):
    """Order status change history"""
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, choices=ServiceOrder.Status.choices)
    new_status = models.CharField(max_length=20, choices=ServiceOrder.Status.choices)
    notes = models.TextField(blank=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Order Status Histories"

    def __str__(self):
        return f"{self.order.order_number} - {self.old_status} → {self.new_status}"


class PointTransaction(TimestampedModel):
    """Customer point transaction history"""

    class TransactionType(models.TextChoices):
        EARNED = 'earned', 'Points Earned'
        REDEEMED = 'redeemed', 'Points Redeemed'
        EXPIRED = 'expired', 'Points Expired'
        ADJUSTED = 'adjusted', 'Manual Adjustment'

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='point_transactions')
    points = models.IntegerField()  # Can be negative for redemptions
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices
    )
    reason = models.CharField(max_length=255)
    order = models.ForeignKey(ServiceOrder, on_delete=models.SET_NULL, null=True, blank=True)

    # Balance tracking
    balance_before = models.PositiveIntegerField(default=0)
    balance_after = models.PositiveIntegerField(default=0)

    # Expiration for earned points
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.user.get_full_name()} - {self.points} pts - {self.get_transaction_type_display()}"

    def save(self, *args, **kwargs):
        if not self.pk:  # New transaction
            self.balance_before = self.customer.total_points
            self.balance_after = self.balance_before + self.points

            # Set expiration for earned points (1 year)
            if self.transaction_type == self.TransactionType.EARNED:
                self.expires_at = timezone.now() + timedelta(days=365)

        super().save(*args, **kwargs)


class LoyaltyReward(TimestampedModel):
    """Loyalty program rewards"""

    class RewardType(models.TextChoices):
        DISCOUNT = 'discount', 'Discount Percentage'
        FIXED_AMOUNT = 'fixed', 'Fixed Amount Off'
        FREE_SERVICE = 'service', 'Free Service'
        GIFT = 'gift', 'Physical Gift'

    name = models.CharField(max_length=200)
    description = models.TextField()
    reward_type = models.CharField(max_length=10, choices=RewardType.choices)

    # Point cost
    points_required = models.PositiveIntegerField()

    # Reward value
    discount_percentage = models.PositiveIntegerField(
        null=True, blank=True,
        validators=[MaxValueValidator(100)]
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )
    free_service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        null=True, blank=True
    )

    # Availability
    is_available = models.BooleanField(default=True)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    current_redemptions = models.PositiveIntegerField(default=0)

    # Restrictions
    minimum_membership_level = models.CharField(
        max_length=20,
        choices=MembershipLevel.choices,
        default=MembershipLevel.BRONZE
    )
    minimum_order_value = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )

    # Media
    image = models.ImageField(upload_to='rewards/', blank=True, null=True)

    class Meta:
        ordering = ['points_required', 'name']

    def __str__(self):
        return f"{self.name} - {self.points_required} pts"

    def is_available_for_customer(self, customer):
        """Check if reward is available for specific customer"""
        if not self.is_available:
            return False

        # Check membership level
        level_order = {
            MembershipLevel.BRONZE: 0,
            MembershipLevel.SILVER: 1,
            MembershipLevel.GOLD: 2,
            MembershipLevel.PLATINUM: 3
        }

        if level_order[customer.membership_level] < level_order[self.minimum_membership_level]:
            return False

        # Check points
        if customer.total_points < self.points_required:
            return False

        # Check date range
        now = timezone.now()
        if self.available_from and now < self.available_from:
            return False
        if self.available_until and now > self.available_until:
            return False

        # Check redemption limit
        if self.max_redemptions and self.current_redemptions >= self.max_redemptions:
            return False

        return True

    def redeem_for_customer(self, customer):
        """Redeem reward for customer"""
        if not self.is_available_for_customer(customer):
            return False

        # Deduct points
        if customer.redeem_points(
                self.points_required,
                f"Redeemed reward: {self.name}"
        ):
            # Create redemption record
            RewardRedemption.objects.create(
                customer=customer,
                reward=self,
                points_used=self.points_required
            )

            # Update redemption count
            self.current_redemptions += 1
            self.save(update_fields=['current_redemptions'])

            return True

        return False


class RewardRedemption(TimestampedModel):
    """Reward redemption history"""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        USED = 'used', 'Used'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='reward_redemptions')
    reward = models.ForeignKey(LoyaltyReward, on_delete=models.CASCADE)
    points_used = models.PositiveIntegerField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Usage tracking
    used_at = models.DateTimeField(null=True, blank=True)
    used_for_order = models.ForeignKey(ServiceOrder, on_delete=models.SET_NULL, null=True, blank=True)
    expires_at = models.DateTimeField()

    # Voucher code for tracking
    voucher_code = models.CharField(max_length=20, unique=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.user.get_full_name()} - {self.reward.name}"

    def save(self, *args, **kwargs):
        if not self.voucher_code:
            self.voucher_code = self.generate_voucher_code()

        if not self.expires_at:
            # Set expiration to 30 days from redemption
            self.expires_at = timezone.now() + timedelta(days=30)

        super().save(*args, **kwargs)

    def generate_voucher_code(self):
        """Generate unique voucher code"""
        import random
        import string
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not RewardRedemption.objects.filter(voucher_code=code).exists():
                return code

    def is_valid(self):
        """Check if redemption is still valid"""
        return (
                self.status in [self.Status.PENDING, self.Status.APPROVED] and
                timezone.now() < self.expires_at
        )

    def use_redemption(self, order=None):
        """Mark redemption as used"""
        if self.is_valid():
            self.status = self.Status.USED
            self.used_at = timezone.now()
            if order:
                self.used_for_order = order
            self.save(update_fields=['status', 'used_at', 'used_for_order'])
            return True
        return False


class CustomerNotification(TimestampedModel):
    """Customer notifications"""

    class NotificationType(models.TextChoices):
        ORDER_UPDATE = 'order_update', 'Order Update'
        PROMOTION = 'promotion', 'Promotion'
        MEMBERSHIP = 'membership', 'Membership'
        SYSTEM = 'system', 'System'
        REMINDER = 'reminder', 'Reminder'

    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM
    )

    # Status
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    # Related objects
    related_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, null=True, blank=True)

    # Action URL
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'is_read']),
        ]

    def __str__(self):
        return f"{self.customer.user.get_full_name()} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class CustomerDevice(TimestampedModel):
    """Customer's registered devices"""
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='devices')
    brand = models.ForeignKey('core.Brand', on_delete=models.CASCADE)
    model = models.CharField(max_length=100)
    serial_number = models.CharField(max_length=100, blank=True)
    purchase_date = models.DateField(null=True, blank=True)

    # Device specifications
    processor = models.CharField(max_length=100, blank=True)
    ram = models.CharField(max_length=50, blank=True)
    storage = models.CharField(max_length=50, blank=True)

    # Service history
    last_service_date = models.DateField(null=True, blank=True)
    service_count = models.PositiveIntegerField(default=0)

    # Notes
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer.user.get_full_name()} - {self.brand.name} {self.model}"


class CustomerPreference(TimestampedModel):
    """Customer preferences and settings"""
    customer = models.OneToOneField(CustomerProfile, on_delete=models.CASCADE, related_name='preferences')

    # Communication preferences
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    whatsapp_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)

    # Marketing preferences
    promotional_emails = models.BooleanField(default=True)
    newsletter = models.BooleanField(default=True)
    special_offers = models.BooleanField(default=True)

    # Service preferences
    preferred_pickup_time = models.CharField(
        max_length=20,
        choices=[
            ('morning', 'Pagi (08:00-12:00)'),
            ('afternoon', 'Siang (12:00-17:00)'),
            ('evening', 'Sore (17:00-20:00)'),
        ],
        default='morning'
    )
    preferred_contact_method = models.CharField(
        max_length=10,
        choices=[
            ('whatsapp', 'WhatsApp'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('sms', 'SMS'),
        ],
        default='whatsapp'
    )

    # Privacy settings
    allow_data_sharing = models.BooleanField(default=False)
    allow_testimonial_use = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Customer Preference"
        verbose_name_plural = "Customer Preferences"

    def __str__(self):
        return f"Preferences for {self.customer.user.get_full_name()}"