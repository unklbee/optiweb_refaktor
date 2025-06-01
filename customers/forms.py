# customers/forms.py
"""
Enhanced customer forms
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password

from .models import CustomerProfile, ServiceOrder
from services.models import Service
from core.forms import BaseModelForm, ContactMixin


class CustomerRegistrationForm(ContactMixin, UserCreationForm):
    """Enhanced registration form with better validation"""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'email@example.com'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Nama depan Anda'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Nama belakang Anda'
        })
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '08xxxxxxxxxx'
        })
    )
    whatsapp = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': '08xxxxxxxxxx (jika berbeda dari nomor telepon)'
        })
    )
    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Alamat lengkap untuk pickup/delivery',
            'rows': 3
        })
    )

    # Terms and conditions
    terms_accepted = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'mr-2 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        }),
        error_messages={
            'required': _('You must accept the terms and conditions to register.')
        }
    )

    # Referral code
    referral_code = forms.CharField(
        max_length=10,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Masukkan kode referral (opsional)'
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Update field attributes
        self.fields['username'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Pilih username unik'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Masukkan password yang kuat'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Konfirmasi password'
        })

        # Update labels
        self.fields['username'].label = _('Username')
        self.fields['email'].label = _('Email Address')
        self.fields['first_name'].label = _('First Name')
        self.fields['last_name'].label = _('Last Name')
        self.fields['password1'].label = _('Password')
        self.fields['password2'].label = _('Confirm Password')
        self.fields['phone'].label = _('Phone Number')
        self.fields['whatsapp'].label = _('WhatsApp Number (Optional)')
        self.fields['address'].label = _('Complete Address (Optional)')
        self.fields['terms_accepted'].label = _('I agree to the terms and conditions')
        self.fields['referral_code'].label = _('Referral Code (Optional)')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if len(username) < 3:
            raise ValidationError(_('Username must be at least 3 characters long.'))
        if not username.replace('_', '').replace('.', '').isalnum():
            raise ValidationError(_('Username can only contain letters, numbers, dots, and underscores.'))
        return username

    def clean_referral_code(self):
        referral_code = self.cleaned_data.get('referral_code')
        if referral_code:
            try:
                CustomerProfile.objects.get(referral_code=referral_code)
            except CustomerProfile.DoesNotExist:
                raise ValidationError(_('Invalid referral code.'))
        return referral_code

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()

            # Create customer profile
            profile = CustomerProfile.objects.create(
                user=user,
                phone=self.cleaned_data['phone'],
                whatsapp=self.cleaned_data['whatsapp'] or self.cleaned_data['phone'],
                address=self.cleaned_data['address']
            )

            # Process referral if provided
            referral_code = self.cleaned_data.get('referral_code')
            if referral_code:
                try:
                    referrer = CustomerProfile.objects.get(referral_code=referral_code)
                    referrer.process_referral(profile)
                except CustomerProfile.DoesNotExist:
                    pass  # Already validated in clean_referral_code

        return user


class ProfileUpdateForm(ContactMixin, BaseModelForm):
    """Enhanced profile update form"""

    first_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('First Name')
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        label=_('Last Name')
    )
    email = forms.EmailField(
        required=True,
        label=_('Email Address')
    )

    class Meta:
        model = CustomerProfile
        fields = [
            'phone', 'whatsapp', 'address', 'city', 'postal_code',
            'birth_date', 'gender', 'avatar',
            'email_notifications', 'whatsapp_notifications',
            'promotional_offers', 'newsletter_subscription'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'avatar': forms.FileInput(attrs={
                'accept': 'image/*',
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
            }),
        }
        placeholders = {
            'phone': '08xxxxxxxxxx',
            'whatsapp': '08xxxxxxxxxx',
            'address': 'Alamat lengkap untuk pickup/delivery',
            'city': 'Nama kota',
            'postal_code': 'Kode pos',
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            self.fields['first_name'].initial = self.user.first_name
            self.fields['last_name'].initial = self.user.last_name
            self.fields['email'].initial = self.user.email

        # Update field labels
        self.fields['phone'].label = _('Phone Number')
        self.fields['whatsapp'].label = _('WhatsApp Number')
        self.fields['address'].label = _('Complete Address')
        self.fields['city'].label = _('City')
        self.fields['postal_code'].label = _('Postal Code')
        self.fields['birth_date'].label = _('Birth Date')
        self.fields['gender'].label = _('Gender')
        self.fields['avatar'].label = _('Profile Picture')
        self.fields['email_notifications'].label = _('Email Notifications')
        self.fields['whatsapp_notifications'].label = _('WhatsApp Notifications')
        self.fields['promotional_offers'].label = _('Promotional Offers')
        self.fields['newsletter_subscription'].label = _('Newsletter Subscription')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.user and User.objects.filter(email=email).exclude(id=self.user.id).exists():
            raise ValidationError(_('A user with this email already exists.'))
        return email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Validate file size (max 5MB)
            if avatar.size > 5 * 1024 * 1024:
                raise ValidationError(_('Image file too large. Maximum size is 5MB.'))

            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if avatar.content_type not in allowed_types:
                raise ValidationError(_('Invalid image format. Please use JPEG, PNG, GIF, or WebP.'))

        return avatar

    def save(self, commit=True):
        profile = super().save(commit=False)

        if commit and self.user:
            # Update user fields
            self.user.first_name = self.cleaned_data['first_name']
            self.user.last_name = self.cleaned_data['last_name']
            self.user.email = self.cleaned_data['email']
            self.user.save()

            profile.save()

        return profile


class ServiceOrderForm(BaseModelForm):
    """Enhanced service order form"""

    # Device images upload
    device_images = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'multiple': True,
            'accept': 'image/*',
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        }),
        label=_('Device Images (Optional)'),
        help_text=_('Upload photos of your device to help with diagnosis')
    )

    class Meta:
        model = ServiceOrder
        fields = [
            'service', 'device_brand', 'device_model', 'device_serial',
            'problem_description', 'priority', 'device_condition'
        ]
        widgets = {
            'problem_description': forms.Textarea(attrs={'rows': 4}),
            'device_condition': forms.Textarea(attrs={'rows': 3}),
            'device_serial': forms.TextInput(attrs={
                'placeholder': 'Opsional - jika diketahui'
            })
        }
        placeholders = {
            'device_brand': 'Contoh: Asus, HP, Acer, Dell',
            'device_model': 'Contoh: VivoBook S14, Pavilion 14',
            'problem_description': 'Jelaskan masalah laptop Anda secara detail...',
            'device_condition': 'Kondisi fisik laptop saat ini (lecet, normal, dll.)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Update field labels
        self.fields['service'].label = _('Service Type')
        self.fields['device_brand'].label = _('Laptop Brand')
        self.fields['device_model'].label = _('Laptop Model/Type')
        self.fields['device_serial'].label = _('Serial Number (Optional)')
        self.fields['problem_description'].label = _('Problem Description')
        self.fields['priority'].label = _('Service Priority')
        self.fields['device_condition'].label = _('Device Physical Condition')

        # Filter only active services
        self.fields['service'].queryset = Service.objects.filter(is_active=True, is_published=True)

        # Group services by category for better UX
        service_choices = [('', '---------')]
        categories = {}

        for service in self.fields['service'].queryset.select_related('category'):
            category_name = service.category.name if service.category else 'Other'
            if category_name not in categories:
                categories[category_name] = []
            categories[category_name].append((service.id, service.name))

        # Add grouped choices
        for category, services in categories.items():
            service_choices.append((category, services))

        self.fields['service'].choices = service_choices

    def clean_device_images(self):
        images = self.files.getlist('device_images')

        if len(images) > 5:
            raise ValidationError(_('Maximum 5 images allowed.'))

        for image in images:
            # Validate file size (max 10MB per image)
            if image.size > 10 * 1024 * 1024:
                raise ValidationError(_('Each image must be less than 10MB.'))

            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if image.content_type not in allowed_types:
                raise ValidationError(_('Invalid image format. Please use JPEG, PNG, GIF, or WebP.'))

        return images

    def clean_problem_description(self):
        description = self.cleaned_data.get('problem_description', '')

        if len(description.strip()) < 10:
            raise ValidationError(_('Please provide a more detailed description (at least 10 characters).'))

        # Check for spam or inappropriate content
        spam_keywords = ['spam', 'test test test', 'asdf', 'qwerty']
        if any(keyword in description.lower() for keyword in spam_keywords):
            raise ValidationError(_('Please provide a meaningful problem description.'))

        return description.strip()


class ServiceSearchForm(forms.Form):
    """Service search and filter form"""

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Search services...'
        })
    )

    category = forms.ModelChoiceField(
        queryset=None,
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Min price'
        })
    )

    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500',
            'placeholder': 'Max price'
        })
    )

    min_rating = forms.ChoiceField(
        choices=[
            ('', 'Any Rating'),
            ('1', '1+ Stars'),
            ('2', '2+ Stars'),
            ('3', '3+ Stars'),
            ('4', '4+ Stars'),
            ('5', '5 Stars'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    sort = forms.ChoiceField(
        choices=[
            ('featured', 'Featured'),
            ('popular', 'Most Popular'),
            ('price_low', 'Price: Low to High'),
            ('price_high', 'Price: High to Low'),
            ('rating', 'Highest Rated'),
            ('newest', 'Newest'),
        ],
        required=False,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from services.models import ServiceCategory
        self.fields['category'].queryset = ServiceCategory.objects.filter(is_published=True)


class ServiceReviewForm(BaseModelForm):
    """Service review form"""

    class Meta:
        model = None  # Will be imported from services.models
        fields = ['rating', 'title', 'review_text']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={
                    'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500'
                }
            ),
            'title': forms.TextInput(attrs={
                'placeholder': 'Summary of your experience'
            }),
            'review_text': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share your detailed experience with this service...'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['rating'].label = _('Overall Rating')
        self.fields['title'].label = _('Review Title (Optional)')
        self.fields['review_text'].label = _('Your Review')

        # Make title optional
        self.fields['title'].required = False

    def clean_review_text(self):
        review_text = self.cleaned_data.get('review_text', '')

        if len(review_text.strip()) < 10:
            raise ValidationError(_('Please provide a more detailed review (at least 10 characters).'))

        return review_text.strip()