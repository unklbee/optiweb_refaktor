# services/forms.py - Additional forms
"""
Additional service-related forms
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class ServiceComparisonForm(forms.Form):
    """Form for comparing services"""

    services = forms.ModelMultipleChoiceField(
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from services.models import Service
        self.fields['services'].queryset = Service.objects.filter(
            is_active=True,
            is_published=True
        )

    def clean_services(self):
        services = self.cleaned_data.get('services')

        if len(services) < 2:
            raise ValidationError(_('Please select at least 2 services to compare.'))

        if len(services) > 4:
            raise ValidationError(_('You can compare maximum 4 services at once.'))

        return services


class ServiceQuoteForm(forms.Form):
    """Form for requesting service quote"""

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Your full name'
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'your.email@example.com'
        })
    )

    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': '08xxxxxxxxxx'
        })
    )

    service = forms.ModelChoiceField(
        queryset=None,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    device_brand = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'e.g., Asus, HP, Acer'
        })
    )

    device_model = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'e.g., VivoBook S14, Pavilion 14'
        })
    )

    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Describe the issue and any specific requirements...',
            'rows': 4
        })
    )

    urgency = forms.ChoiceField(
        choices=[
            ('normal', 'Normal (3-5 days)'),
            ('priority', 'Priority (1-2 days)'),
            ('express', 'Express (Same day)'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from services.models import Service
        self.fields['service'].queryset = Service.objects.filter(
            is_active=True,
            is_published=True
        )

        # Update labels
        self.fields['name'].label = _('Full Name')
        self.fields['email'].label = _('Email Address')
        self.fields['phone'].label = _('Phone Number')
        self.fields['service'].label = _('Service Needed')
        self.fields['device_brand'].label = _('Device Brand')
        self.fields['device_model'].label = _('Device Model')
        self.fields['description'].label = _('Issue Description')
        self.fields['urgency'].label = _('Urgency Level')

    def clean_description(self):
        description = self.cleaned_data.get('description', '')

        if len(description.strip()) < 20:
            raise ValidationError(_('Please provide a more detailed description (at least 20 characters).'))

        return description.strip()