# core/forms.py
"""
Base forms and mixins
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User


class BaseModelForm(forms.ModelForm):
    """Base form with common functionality"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_common_css_classes()
        self.add_placeholders()

    def add_common_css_classes(self):
        """Add common CSS classes to form fields"""
        for field_name, field in self.fields.items():
            if isinstance(field.widget, (forms.TextInput, forms.EmailInput, forms.URLInput)):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                })
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                })
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
                })

    def add_placeholders(self):
        """Add placeholders to form fields"""
        placeholders = getattr(self.Meta, 'placeholders', {})
        for field_name, placeholder in placeholders.items():
            if field_name in self.fields:
                self.fields[field_name].widget.attrs['placeholder'] = placeholder


class ContactMixin:
    """Mixin for contact information validation"""

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone:
            # Remove non-digit characters
            phone_digits = ''.join(filter(str.isdigit, phone))

            # Validate Indonesian phone number
            if not phone_digits.startswith(('08', '628')):
                raise ValidationError(_('Please enter a valid Indonesian phone number'))

            if len(phone_digits) < 10 or len(phone_digits) > 13:
                raise ValidationError(_('Phone number must be between 10-13 digits'))

        return phone

    def clean_whatsapp(self):
        whatsapp = self.cleaned_data.get('whatsapp', '')
        if whatsapp:
            # Same validation as phone
            whatsapp_digits = ''.join(filter(str.isdigit, whatsapp))

            if not whatsapp_digits.startswith(('08', '628')):
                raise ValidationError(_('Please enter a valid Indonesian WhatsApp number'))

            if len(whatsapp_digits) < 10 or len(whatsapp_digits) > 13:
                raise ValidationError(_('WhatsApp number must be between 10-13 digits'))

        return whatsapp