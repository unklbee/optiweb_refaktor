# core/utils.py - Utility functions
import hashlib
import random
import string
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class OrderNumberGenerator:
    """Generate unique order numbers"""
    PREFIX = 'SLB'

    @classmethod
    def generate(cls):
        """Generate unique order number"""
        timestamp = timezone.now().strftime('%Y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"{cls.PREFIX}-{timestamp}-{random_suffix}"

    @classmethod
    def generate_invoice_number(cls):
        """Generate invoice number"""
        timestamp = timezone.now().strftime('%Y%m')
        random_suffix = ''.join(random.choices(string.digits, k=6))
        return f"INV-{timestamp}-{random_suffix}"

    @classmethod
    def generate_reference_number(cls, prefix='REF'):
        """Generate reference number with custom prefix"""
        timestamp = timezone.now().strftime('%Y%m%d%H%M')
        random_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{prefix}-{timestamp}-{random_suffix}"


class PriceCalculator:
    """Calculate service prices based on various factors"""

    @staticmethod
    def calculate_service_price(base_price, brand_multiplier=1.0, complexity_multiplier=1.0,
                                urgency_multiplier=1.0, member_discount=0.0):
        """Calculate final service price"""
        price = Decimal(str(base_price))
        price *= Decimal(str(brand_multiplier))
        price *= Decimal(str(complexity_multiplier))
        price *= Decimal(str(urgency_multiplier))

        # Apply member discount
        if member_discount > 0:
            discount_amount = price * Decimal(str(member_discount / 100))
            price -= discount_amount

        return price.quantize(Decimal('0.01'))

    @staticmethod
    def calculate_pickup_fee(distance_km, base_fee=25000):
        """Calculate pickup/delivery fee based on distance"""
        if distance_km <= 5:
            return Decimal('0.00')  # Free for nearby areas
        elif distance_km <= 10:
            return Decimal(str(base_fee))
        else:
            # Additional fee for distant areas
            extra_km = distance_km - 10
            extra_fee = extra_km * 2000  # 2000 per km
            return Decimal(str(base_fee + extra_fee))

    @staticmethod
    def calculate_tax(amount, tax_rate=0.11):
        """Calculate tax (PPN 11%)"""
        return (Decimal(str(amount)) * Decimal(str(tax_rate))).quantize(Decimal('0.01'))

    @staticmethod
    def calculate_total_with_tax(subtotal, tax_rate=0.11):
        """Calculate total including tax"""
        tax = PriceCalculator.calculate_tax(subtotal, tax_rate)
        return subtotal + tax


class NotificationService:
    """Service for sending notifications"""

    @staticmethod
    def send_email_notification(subject, template_name, context, recipient_list,
                                from_email=None, attachments=None):
        """Send email notification using template"""
        try:
            from_email = from_email or settings.DEFAULT_FROM_EMAIL

            # Render email templates
            html_message = render_to_string(template_name, context)
            text_message = render_to_string(
                template_name.replace('.html', '.txt'),
                context
            ) if template_name.endswith('.html') else strip_tags(html_message)

            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=from_email,
                to=recipient_list
            )

            # Attach HTML version
            email.attach_alternative(html_message, "text/html")

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    email.attach_file(attachment)

            # Send email
            email.send()

            logger.info(f"Email sent successfully to {recipient_list}")
            return True

        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False

    @staticmethod
    def send_whatsapp_notification(phone_number, message, template_name=None):
        """Send WhatsApp notification (implement with WhatsApp API)"""
        # Placeholder for WhatsApp API integration
        # This would integrate with services like Twilio, MessageBird, etc.
        try:
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '+62' + phone_number[1:]
            elif not phone_number.startswith('+'):
                phone_number = '+62' + phone_number

            # Here you would integrate with WhatsApp Business API
            # For now, we'll just log the message
            logger.info(f"WhatsApp message to {phone_number}: {message}")

            return True
        except Exception as e:
            logger.error(f"WhatsApp sending failed: {e}")
            return False

    @staticmethod
    def send_sms_notification(phone_number, message):
        """Send SMS notification"""
        try:
            # Format phone number
            if phone_number.startswith('0'):
                phone_number = '+62' + phone_number[1:]
            elif not phone_number.startswith('+'):
                phone_number = '+62' + phone_number

            # Here you would integrate with SMS service provider
            # For now, we'll just log the message
            logger.info(f"SMS to {phone_number}: {message}")

            return True
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False

    @staticmethod
    def send_push_notification(user_tokens, title, body, data=None):
        """Send push notification to mobile devices"""
        try:
            # Here you would integrate with Firebase Cloud Messaging or similar
            logger.info(f"Push notification: {title} - {body}")
            return True
        except Exception as e:
            logger.error(f"Push notification failed: {e}")
            return False


class SEOHelper:
    """Helper class for SEO operations"""

    @staticmethod
    def generate_meta_title(title, business_name="Service Laptop Bandung"):
        """Generate SEO-friendly meta title"""
        if len(title) > 50:
            title = title[:47] + "..."
        return f"{title} | {business_name}"

    @staticmethod
    def generate_meta_description(content, max_length=160):
        """Generate meta description from content"""
        if not content:
            return ""

        clean_content = strip_tags(content)
        if len(clean_content) <= max_length:
            return clean_content

        # Truncate at word boundary
        words = clean_content.split()
        description = ""
        for word in words:
            if len(description + " " + word) > max_length - 3:
                break
            description += " " + word if description else word

        return description + "..."

    @staticmethod
    def generate_slug(text, max_length=50):
        """Generate SEO-friendly slug"""
        from django.utils.text import slugify
        slug = slugify(text)
        if len(slug) > max_length:
            slug = slug[:max_length].rsplit('-', 1)[0]
        return slug

    @staticmethod
    def extract_keywords(text, max_keywords=10):
        """Extract keywords from text"""
        import re

        # Remove HTML tags and normalize text
        clean_text = strip_tags(text).lower()

        # Remove common stop words (Indonesian)
        stop_words = {
            'adalah', 'ada', 'agar', 'akan', 'aku', 'atau', 'dan', 'dari',
            'dalam', 'dengan', 'di', 'ini', 'itu', 'jika', 'karena', 'ke',
            'kepada', 'oleh', 'pada', 'sama', 'sampai', 'saya', 'se', 'sudah',
            'untuk', 'yang', 'ya', 'telah', 'dapat', 'bisa', 'maka'
        }

        # Extract words (minimum 3 characters)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', clean_text)

        # Count word frequency
        word_count = {}
        for word in words:
            if word not in stop_words:
                word_count[word] = word_count.get(word, 0) + 1

        # Sort by frequency and return top keywords
        sorted_keywords = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_keywords[:max_keywords]]


class ImageOptimizer:
    """Image optimization utilities"""

    @staticmethod
    def resize_image(image_path, max_width=800, max_height=600, quality=85):
        """Resize and optimize images"""
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Calculate new dimensions
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

                # Save optimized image
                img.save(image_path, 'JPEG', quality=quality, optimize=True)
                return True
        except Exception as e:
            logger.error(f"Image optimization failed: {e}")
            return False

    @staticmethod
    def create_thumbnail(image_path, thumbnail_path, size=(300, 300)):
        """Create thumbnail from image"""
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')

                # Create thumbnail
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)
                return True
        except Exception as e:
            logger.error(f"Thumbnail creation failed: {e}")
            return False

    @staticmethod
    def get_image_dimensions(image_path):
        """Get image dimensions"""
        try:
            from PIL import Image

            with Image.open(image_path) as img:
                return img.size
        except Exception as e:
            logger.error(f"Getting image dimensions failed: {e}")
            return None


class CacheHelper:
    """Helper for cache operations"""

    @staticmethod
    def get_cache_key(*args, **kwargs):
        """Generate consistent cache key"""
        key_parts = []

        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))

        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}_{value}")

        return ":".join(key_parts)

    @staticmethod
    def cache_model_instance(instance, timeout=3600):
        """Cache a model instance"""
        from django.core.cache import cache

        cache_key = f"{instance.__class__.__name__}_{instance.pk}"
        cache.set(cache_key, instance, timeout)
        return cache_key

    @staticmethod
    def get_cached_model_instance(model_class, pk):
        """Get cached model instance"""
        from django.core.cache import cache

        cache_key = f"{model_class.__name__}_{pk}"
        return cache.get(cache_key)

    @staticmethod
    def invalidate_model_cache(model_class, pk):
        """Invalidate cached model instance"""
        from django.core.cache import cache

        cache_key = f"{model_class.__name__}_{pk}"
        cache.delete(cache_key)


class ValidationHelper:
    """Helper for data validation"""

    @staticmethod
    def validate_indonesian_phone(phone_number):
        """Validate Indonesian phone number"""
        import re

        # Remove non-digit characters
        digits = re.sub(r'\D', '', phone_number)

        # Check if it starts with valid Indonesian prefixes
        valid_prefixes = ['08', '628', '62']

        for prefix in valid_prefixes:
            if digits.startswith(prefix):
                # Check length
                if prefix == '08' and 10 <= len(digits) <= 13:
                    return True
                elif prefix in ['628', '62'] and 12 <= len(digits) <= 15:
                    return True

        return False

    @staticmethod
    def format_indonesian_phone(phone_number):
        """Format Indonesian phone number to international format"""
        import re

        # Remove non-digit characters
        digits = re.sub(r'\D', '', phone_number)

        # Convert to international format
        if digits.startswith('0'):
            return '+62' + digits[1:]
        elif digits.startswith('62'):
            return '+' + digits
        else:
            return '+62' + digits

    @staticmethod
    def validate_email_domain(email):
        """Validate email domain (check for common disposable email providers)"""
        disposable_domains = {
            '10minutemail.com', 'guerrillamail.com', 'mailinator.com',
            'tempmail.org', 'yopmail.com', 'throwaway.email'
        }

        try:
            domain = email.split('@')[1].lower()
            return domain not in disposable_domains
        except (IndexError, AttributeError):
            return False


class FileHelper:
    """Helper for file operations"""

    @staticmethod
    def get_file_extension(filename):
        """Get file extension"""
        import os
        return os.path.splitext(filename)[1].lower()

    @staticmethod
    def is_allowed_file_type(filename, allowed_types):
        """Check if file type is allowed"""
        extension = FileHelper.get_file_extension(filename)
        return extension in allowed_types

    @staticmethod
    def generate_unique_filename(filename):
        """Generate unique filename"""
        import os
        import uuid

        name, ext = os.path.splitext(filename)
        unique_name = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        return unique_name

    @staticmethod
    def get_file_size_mb(file_path):
        """Get file size in MB"""
        import os

        try:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except OSError:
            return 0


class DateTimeHelper:
    """Helper for date and time operations"""

    @staticmethod
    def format_duration(duration):
        """Format duration for display"""
        if not duration:
            return ""

        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60

        if hours > 0:
            return f"{hours} jam {minutes} menit"
        else:
            return f"{minutes} menit"

    @staticmethod
    def get_business_days_between(start_date, end_date):
        """Calculate business days between two dates"""
        from datetime import timedelta

        current_date = start_date
        business_days = 0

        while current_date <= end_date:
            # Monday = 0, Sunday = 6
            if current_date.weekday() < 5:  # Monday to Friday
                business_days += 1
            current_date += timedelta(days=1)

        return business_days

    @staticmethod
    def is_business_hours(dt=None):
        """Check if current time is within business hours"""
        if dt is None:
            dt = timezone.now()

        # Business hours: Monday-Friday 8:00-17:00, Saturday 8:00-12:00
        weekday = dt.weekday()  # Monday = 0, Sunday = 6
        hour = dt.hour

        if weekday < 5:  # Monday to Friday
            return 8 <= hour < 17
        elif weekday == 5:  # Saturday
            return 8 <= hour < 12
        else:  # Sunday
            return False

    @staticmethod
    def get_next_business_day(dt=None):
        """Get next business day"""
        from datetime import timedelta

        if dt is None:
            dt = timezone.now().date()

        next_day = dt + timedelta(days=1)

        # Skip weekends
        while next_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
            next_day += timedelta(days=1)

        return next_day

    @staticmethod
    def format_relative_time(dt):
        """Format time relative to now (e.g., '2 hours ago')"""
        from django.utils.timesince import timesince
        from django.utils.timeuntil import timeuntil

        now = timezone.now()

        if dt > now:
            return f"dalam {timeuntil(dt)}"
        else:
            return f"{timesince(dt)} yang lalu"


class NumberHelper:
    """Helper for number formatting"""

    @staticmethod
    def format_currency(amount, currency="Rp"):
        """Format amount as currency"""
        if isinstance(amount, str):
            try:
                amount = float(amount)
            except ValueError:
                return f"{currency} 0"

        return f"{currency} {amount:,.0f}".replace(',', '.')

    @staticmethod
    def format_percentage(value, decimal_places=1):
        """Format value as percentage"""
        if isinstance(value, str):
            try:
                value = float(value)
            except ValueError:
                return "0%"

        return f"{value:.{decimal_places}f}%"

    @staticmethod
    def parse_currency(currency_string):
        """Parse currency string to decimal"""
        import re

        # Remove currency symbols and spaces
        clean_string = re.sub(r'[^\d,.-]', '', currency_string)

        # Handle Indonesian number format (dot as thousands separator)
        if ',' in clean_string and '.' in clean_string:
            # Both comma and dot present
            if clean_string.rfind('.') > clean_string.rfind(','):
                # Dot is decimal separator
                clean_string = clean_string.replace(',', '')
            else:
                # Comma is decimal separator
                clean_string = clean_string.replace('.', '').replace(',', '.')
        elif '.' in clean_string and len(clean_string.split('.')[-1]) == 3:
            # Dot as thousands separator
            clean_string = clean_string.replace('.', '')
        elif ',' in clean_string:
            # Comma as decimal separator
            clean_string = clean_string.replace(',', '.')

        try:
            return Decimal(clean_string)
        except (ValueError, TypeError):
            return Decimal('0')


class TextHelper:
    """Helper for text processing"""

    @staticmethod
    def truncate_words(text, word_count, suffix='...'):
        """Truncate text to specified word count"""
        words = text.split()
        if len(words) <= word_count:
            return text

        return ' '.join(words[:word_count]) + suffix

    @staticmethod
    def extract_numbers(text):
        """Extract all numbers from text"""
        import re
        return re.findall(r'\d+', text)

    @staticmethod
    def clean_phone_number(phone):
        """Clean phone number string"""
        import re
        return re.sub(r'[^\d+]', '', phone)

    @staticmethod
    def mask_email(email):
        """Mask email for privacy"""
        try:
            username, domain = email.split('@')
            if len(username) <= 2:
                masked_username = username
            else:
                masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
            return f"{masked_username}@{domain}"
        except ValueError:
            return email

    @staticmethod
    def mask_phone(phone):
        """Mask phone number for privacy"""
        if len(phone) <= 4:
            return phone

        return phone[:2] + '*' * (len(phone) - 4) + phone[-2:]

    @staticmethod
    def generate_password(length=12):
        """Generate random password"""
        import secrets

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password


class SecurityHelper:
    """Helper for security operations"""

    @staticmethod
    def hash_string(text, salt=''):
        """Hash string with optional salt"""
        return hashlib.sha256((text + salt).encode()).hexdigest()

    @staticmethod
    def generate_token(length=32):
        """Generate secure random token"""
        import secrets
        return secrets.token_urlsafe(length)

    @staticmethod
    def mask_sensitive_data(data, mask_char='*'):
        """Mask sensitive data"""
        if isinstance(data, str):
            if len(data) <= 4:
                return data
            return data[:2] + mask_char * (len(data) - 4) + data[-2:]
        return data

    @staticmethod
    def is_safe_url(url, allowed_hosts=None):
        """Check if URL is safe for redirects"""
        from urllib.parse import urlparse

        if not url:
            return False

        parsed = urlparse(url)

        # Allow relative URLs
        if not parsed.netloc:
            return True

        # Check against allowed hosts
        if allowed_hosts:
            return parsed.netloc in allowed_hosts

        # Default to settings.ALLOWED_HOSTS
        return parsed.netloc in getattr(settings, 'ALLOWED_HOSTS', [])


class BusinessLogicHelper:
    """Helper for business logic calculations"""

    @staticmethod
    def calculate_loyalty_points(amount, rate=0.01):
        """Calculate loyalty points earned from purchase"""
        return int(Decimal(str(amount)) * Decimal(str(rate)))

    @staticmethod
    def calculate_membership_tier(points):
        """Calculate membership tier based on points"""
        if points >= 10000:
            return 'platinum'
        elif points >= 5000:
            return 'gold'
        elif points >= 2000:
            return 'silver'
        else:
            return 'bronze'

    @staticmethod
    def calculate_service_priority_multiplier(priority):
        """Get price multiplier for service priority"""
        multipliers = {
            'standard': 1.0,
            'express': 1.5,
            'emergency': 2.0
        }
        return multipliers.get(priority, 1.0)

    @staticmethod
    def calculate_warranty_expiry(start_date, warranty_days):
        """Calculate warranty expiry date"""
        return start_date + timedelta(days=warranty_days)

    @staticmethod
    def is_warranty_valid(purchase_date, warranty_days):
        """Check if warranty is still valid"""
        expiry_date = BusinessLogicHelper.calculate_warranty_expiry(
            purchase_date, warranty_days
        )
        return timezone.now().date() <= expiry_date

    @staticmethod
    def calculate_estimated_completion(base_duration, priority='standard', complexity=1.0):
        """Calculate estimated completion time"""
        # Adjust for priority
        priority_factors = {
            'standard': 1.0,
            'express': 0.7,
            'emergency': 0.5
        }

        priority_factor = priority_factors.get(priority, 1.0)

        # Apply complexity and priority factors
        adjusted_duration = base_duration * complexity * priority_factor

        completion_time = timezone.now() + adjusted_duration

        # Adjust for business hours
        if not DateTimeHelper.is_business_hours(completion_time):
            # Move to next business day if outside business hours
            next_business_day = DateTimeHelper.get_next_business_day(completion_time.date())
            completion_time = completion_time.replace(
                year=next_business_day.year,
                month=next_business_day.month,
                day=next_business_day.day,
                hour=9,  # Start of business day
                minute=0,
                second=0
            )

        return completion_time


class ReportHelper:
    """Helper for generating reports"""

    @staticmethod
    def generate_sales_summary(start_date, end_date):
        """Generate sales summary for date range"""
        from customers.models import ServiceOrder
        from django.db.models import Count, Sum, Avg

        orders = ServiceOrder.objects.filter(
            created_at__date__range=[start_date, end_date],
            status__in=['completed', 'delivered']
        )

        summary = orders.aggregate(
            total_orders=Count('id'),
            total_revenue=Sum('final_cost'),
            average_order_value=Avg('final_cost')
        )

        return summary

    @staticmethod
    def generate_service_performance_report(start_date, end_date):
        """Generate service performance report"""
        from customers.models import ServiceOrder
        from services.models import Service
        from django.db.models import Count, Avg

        # Get service statistics
        service_stats = Service.objects.annotate(
            order_count=Count('serviceorder'),
            avg_rating=Avg('reviews__rating')
        ).filter(
            serviceorder__created_at__date__range=[start_date, end_date]
        )

        return service_stats

    @staticmethod
    def generate_customer_analytics(start_date, end_date):
        """Generate customer analytics"""
        from customers.models import CustomerProfile, ServiceOrder
        from django.db.models import Count, Sum

        # New customers
        new_customers = CustomerProfile.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count()

        # Repeat customers
        repeat_customers = CustomerProfile.objects.filter(
            orders__created_at__date__range=[start_date, end_date]
        ).annotate(
            order_count=Count('orders')
        ).filter(order_count__gt=1).count()

        return {
            'new_customers': new_customers,
            'repeat_customers': repeat_customers,
            'repeat_rate': (repeat_customers / new_customers * 100) if new_customers > 0 else 0
        }


class ImportExportHelper:
    """Helper for import/export operations"""

    @staticmethod
    def export_to_csv(queryset, filename, fields=None):
        """Export queryset to CSV"""
        import csv
        from django.http import HttpResponse

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Write header
        if fields:
            writer.writerow(fields)
        else:
            # Use model field names
            model = queryset.model
            fields = [field.name for field in model._meta.fields]
            writer.writerow(fields)

        # Write data
        for obj in queryset:
            row = []
            for field in fields:
                value = getattr(obj, field, '')
                if callable(value):
                    value = value()
                row.append(str(value))
            writer.writerow(row)

        return response

    @staticmethod
    def import_from_csv(file_path, model_class, field_mapping=None):
        """Import data from CSV file"""
        import csv

        created_count = 0
        error_count = 0
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Map fields if mapping provided
                        if field_mapping:
                            mapped_row = {}
                            for csv_field, model_field in field_mapping.items():
                                if csv_field in row:
                                    mapped_row[model_field] = row[csv_field]
                            row = mapped_row

                        # Create object
                        obj = model_class.objects.create(**row)
                        created_count += 1

                    except Exception as e:
                        error_count += 1
                        errors.append(f"Row {row_num}: {str(e)}")

        except Exception as e:
            errors.append(f"File error: {str(e)}")

        return {
            'created_count': created_count,
            'error_count': error_count,
            'errors': errors
        }