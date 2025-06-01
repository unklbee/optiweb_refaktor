# apps/core/validators.py - Custom validators
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


def validate_phone_number(value):
    """Validate Indonesian phone number format"""
    pattern = r'^(\+62|62|0)[0-9]{8,12}$'
    if not re.match(pattern, value.replace('-', '').replace(' ', '')):
        raise ValidationError(_('Enter a valid Indonesian phone number'))


def validate_order_priority(value):
    """Validate order priority"""
    valid_priorities = ['low', 'medium', 'high', 'urgent']
    if value.lower() not in valid_priorities:
        raise ValidationError(_('Invalid priority level'))


def validate_file_size(value):
    """Validate uploaded file size (max 5MB)"""
    if value.size > 5 * 1024 * 1024:  # 5MB
        raise ValidationError(_('File size cannot exceed 5MB'))


def validate_image_format(value):
    """Validate image format"""
    valid_formats = ['JPEG', 'JPG', 'PNG', 'WebP']
    try:
        from PIL import Image
        img = Image.open(value)
        if img.format not in valid_formats:
            raise ValidationError(_('Unsupported image format'))
    except Exception:
        raise ValidationError(_('Invalid image file'))