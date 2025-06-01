# apps/core/utils.py - Utility functions
import hashlib
import random
import string
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags


class OrderNumberGenerator:
    """Generate unique order numbers"""
    PREFIX = 'SLB'

    @classmethod
    def generate(cls):
        """Generate unique order number"""
        timestamp = timezone.now().strftime('%Y%m%d')
        random_suffix = ''.join(random.choices(string.digits, k=4))
        return f"{cls.PREFIX}-{timestamp}-{random_suffix}"


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


class NotificationService:
    """Service for sending notifications"""

    @staticmethod
    def send_email_notification(subject, template_name, context, recipient_list):
        """Send email notification using template"""
        try:
            html_message = render_to_string(template_name, context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False
            )
            return True
        except Exception as e:
            # Log the error
            print(f"Email sending failed: {e}")
            return False

    @staticmethod
    def send_whatsapp_notification(phone_number, message):
        """Send WhatsApp notification (implement with WhatsApp API)"""
        # Placeholder for WhatsApp API integration
        pass


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


class ImageOptimizer:
    """Image optimization utilities"""

    @staticmethod
    def resize_image(image_path, max_width=800, max_height=600, quality=85):
        """Resize and optimize images"""
        from PIL import Image

        try:
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
            print(f"Image optimization failed: {e}")
            return False