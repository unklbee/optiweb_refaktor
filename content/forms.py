# content/forms.py
"""
Content forms
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import ContactSubmission
from core.forms import BaseModelForm, ContactMixin


class ContactForm(ContactMixin, BaseModelForm):
    """Enhanced contact form"""

    class Meta:
        model = ContactSubmission
        fields = [
            'name', 'email', 'phone', 'inquiry_type',
            'laptop_brand', 'issue_description'
        ]
        widgets = {
            'issue_description': forms.Textarea(attrs={'rows': 5})
        }
        placeholders = {
            'name': 'Your full name',
            'email': 'your.email@example.com',
            'phone': '08xxxxxxxxxx',
            'laptop_brand': 'e.g., Asus, HP, Acer, Dell',
            'issue_description': 'Please describe your laptop issue in detail...'
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Update field labels
        self.fields['name'].label = _('Full Name')
        self.fields['email'].label = _('Email Address')
        self.fields['phone'].label = _('Phone/WhatsApp Number')
        self.fields['inquiry_type'].label = _('Type of Inquiry')
        self.fields['laptop_brand'].label = _('Laptop Brand')
        self.fields['issue_description'].label = _('Issue Description')

        # Make phone optional
        self.fields['phone'].required = False
        self.fields['laptop_brand'].required = False

    def clean_issue_description(self):
        description = self.cleaned_data.get('issue_description', '')

        if len(description.strip()) < 20:
            raise ValidationError(_('Please provide a more detailed description (at least 20 characters).'))

        return description.strip()


class NewsletterSubscriptionForm(forms.Form):
    """Newsletter subscription form"""

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-l-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Enter your email address'
        })
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')

        # Check if already subscribed
        try:
            from .models import NewsletterSubscription
            if NewsletterSubscription.objects.filter(email=email).exists():
                raise ValidationError(_('This email is already subscribed to our newsletter.'))
        except ImportError:
            pass  # Model doesn't exist yet

        return email