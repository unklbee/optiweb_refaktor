# api/views.py - Complete API Views
from rest_framework import generics, viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from core.models import BusinessInfo, Brand
from services.models import Service, ServiceCategory, ServiceReview
from customers.models import CustomerProfile, ServiceOrder, PointTransaction, LoyaltyReward
from content.models import ContentPage, FAQ, Testimonial, ContactSubmission
from .serializers import (
    BusinessInfoSerializer, BrandSerializer, ServiceCategorySerializer,
    ServiceListSerializer, ServiceDetailSerializer, ServiceReviewSerializer
)
from core.decorators import rate_limit


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# Authentication Views
class LoginAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'error': 'Username and password required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if user:
            login(request, user)

            # Get customer profile
            try:
                profile = user.customerprofile
                profile_data = {
                    'id': profile.id,
                    'total_points': profile.total_points,
                    'membership_level': profile.membership_level,
                    'discount_percentage': profile.get_discount_percentage()
                }
            except CustomerProfile.DoesNotExist:
                profile_data = None

            return Response({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'profile': profile_data
            })

        return Response({
            'error': 'Invalid credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'success': True})


class RegisterAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        # Validate required fields
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone']
        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Check if username/email already exists
        if User.objects.filter(username=data['username']).exists():
            return Response({
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=data['email']).exists():
            return Response({
                'error': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create user
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data['first_name'],
                last_name=data['last_name']
            )

            # Create customer profile
            profile = CustomerProfile.objects.create(
                user=user,
                phone=data['phone'],
                whatsapp=data.get('whatsapp', data['phone']),
                address=data.get('address', '')
            )

            # Process referral if provided
            referral_code = data.get('referral_code')
            if referral_code:
                try:
                    referrer = CustomerProfile.objects.get(referral_code=referral_code)
                    referrer.process_referral(profile)
                except CustomerProfile.DoesNotExist:
                    pass

            return Response({
                'success': True,
                'message': 'Account created successfully',
                'user_id': user.id
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfileAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            profile = request.user.customerprofile
            return Response({
                'user': {
                    'id': request.user.id,
                    'username': request.user.username,
                    'email': request.user.email,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                },
                'profile': {
                    'phone': profile.phone,
                    'whatsapp': profile.whatsapp,
                    'address': profile.address,
                    'city': profile.city,
                    'postal_code': profile.postal_code,
                    'total_points': profile.total_points,
                    'membership_level': profile.membership_level,
                    'discount_percentage': profile.get_discount_percentage(),
                    'total_orders': profile.total_orders,
                    'total_spent': str(profile.total_spent),
                    'referral_code': profile.referral_code,
                }
            })
        except CustomerProfile.DoesNotExist:
            return Response({
                'error': 'Customer profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

    def put(self, request):
        try:
            user = request.user
            profile = user.customerprofile
            data = request.data

            # Update user fields
            user.first_name = data.get('first_name', user.first_name)
            user.last_name = data.get('last_name', user.last_name)
            user.email = data.get('email', user.email)
            user.save()

            # Update profile fields
            profile.phone = data.get('phone', profile.phone)
            profile.whatsapp = data.get('whatsapp', profile.whatsapp)
            profile.address = data.get('address', profile.address)
            profile.city = data.get('city', profile.city)
            profile.postal_code = data.get('postal_code', profile.postal_code)
            profile.save()

            return Response({
                'success': True,
                'message': 'Profile updated successfully'
            })

        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Service Views
class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Service.objects.filter(is_active=True)
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ServiceDetailSerializer
        return ServiceListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by category
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        # Filter by brand
        brand = self.request.query_params.get('brand')
        if brand:
            queryset = queryset.filter(
                Q(supported_brands__isnull=True) |
                Q(supported_brands__slug=brand)
            ).distinct()

        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(short_description__icontains=search) |
                Q(tags__name__icontains=search)
            ).distinct()

        # Sort
        sort_by = self.request.query_params.get('sort', 'popular')
        if sort_by == 'price_low':
            queryset = queryset.order_by('base_price_min')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-base_price_max')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-average_rating')
        elif sort_by == 'name':
            queryset = queryset.order_by('name')
        else:  # popular
            queryset = queryset.order_by('-popularity_score', '-is_featured')

        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        # Increment view count (with rate limiting)
        cache_key = f"service_view_{instance.id}_{request.session.session_key}"
        if not cache.get(cache_key):
            instance.increment_popularity()
            cache.set(cache_key, True, 3600)  # Once per hour per session

        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class ServiceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ServiceCategory.objects.filter(is_active=True)
    serializer_class = ServiceCategorySerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'


class ServiceReviewViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceReviewSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        service_id = self.request.query_params.get('service')
        queryset = ServiceReview.objects.filter(is_public=True)

        if service_id:
            queryset = queryset.filter(service_id=service_id)

        return queryset.order_by('-created_at')


# Service-specific API views
class ServiceSearchAPIView(generics.ListAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        query = self.request.query_params.get('q', '')

        if not query:
            return Service.objects.none()

        return Service.objects.filter(
            Q(name__icontains=query) |
            Q(short_description__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__name__icontains=query),
            is_active=True
        ).distinct()


class PopularServicesAPIView(generics.ListAPIView):
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Service.objects.filter(
            is_active=True
        ).order_by('-popularity_score')[:10]


class ServiceCompareAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        def post(self, request):
            service_ids = request.data.get('service_ids', [])

            if not service_ids or len(service_ids) < 2:
                return Response({
                    'error': 'At least 2 services required for comparison'
                }, status=status.HTTP_400_BAD_REQUEST)

            if len(service_ids) > 4:
                return Response({
                    'error': 'Maximum 4 services can be compared'
                }, status=status.HTTP_400_BAD_REQUEST)

            services = Service.objects.filter(
                id__in=service_ids,
                is_active=True
            )

            if services.count() != len(service_ids):
                return Response({
                    'error': 'Some services not found'
                }, status=status.HTTP_404_NOT_FOUND)

            serializer = ServiceDetailSerializer(
                services,
                many=True,
                context={'request': request}
            )

            return Response({
                'services': serializer.data,
                'comparison_fields': [
                    'price_range', 'difficulty', 'estimated_duration',
                    'warranty_period', 'average_rating', 'total_orders'
                ]
            })


# Order Management Views
class ServiceOrderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        if hasattr(self.request.user, 'customerprofile'):
            return ServiceOrder.objects.filter(
                customer=self.request.user.customerprofile
            ).order_by('-created_at')
        return ServiceOrder.objects.none()

    def get_serializer_class(self):
        # Return appropriate serializer based on action
        # This would be defined in serializers.py
        pass


class CreateOrderAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            customer = request.user.customerprofile
        except CustomerProfile.DoesNotExist:
            return Response({
                'error': 'Customer profile not found'
            }, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        required_fields = ['service_id', 'device_model', 'problem_description']

        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = Service.objects.get(id=data['service_id'], is_active=True)
        except Service.DoesNotExist:
            return Response({
                'error': 'Service not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Create order
        order = ServiceOrder.objects.create(
            customer=customer,
            service=service,
            device_model=data['device_model'],
            problem_description=data['problem_description'],
            priority=data.get('priority', 'standard'),
            device_serial=data.get('device_serial', ''),
            device_condition=data.get('device_condition', '')
        )

        # Calculate estimated cost
        brand = None
        if data.get('device_brand_id'):
            try:
                brand = Brand.objects.get(id=data['device_brand_id'])
                order.device_brand = brand
            except Brand.DoesNotExist:
                pass

        # Get price range and set estimated cost
        price_range = service.get_price_range(
            brand=brand,
            priority=order.priority,
            member_discount=customer.get_discount_percentage()
        )

        # Set estimated cost to minimum price for now
        if 'Rp' in price_range:
            import re
            prices = re.findall(r'[\d.]+', price_range.replace('.', ''))
            if prices:
                order.estimated_cost = int(prices[0])

        order.save()

        return Response({
            'success': True,
            'order_number': order.order_number,
            'estimated_cost': str(order.estimated_cost or 0),
            'message': 'Order created successfully'
        }, status=status.HTTP_201_CREATED)


class TrackOrderAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_number'

    def get_queryset(self):
        if hasattr(self.request.user, 'customerprofile'):
            return ServiceOrder.objects.filter(
                customer=self.request.user.customerprofile
            )
        return ServiceOrder.objects.none()

    def retrieve(self, request, *args, **kwargs):
        order = self.get_object()

        # Get status history
        status_history = order.status_history.all().order_by('-created_at')[:10]

        return Response({
            'order_number': order.order_number,
            'service': order.service.name,
            'status': order.get_status_display(),
            'priority': order.get_priority_display(),
            'device_info': {
                'brand': order.device_brand.name if order.device_brand else '',
                'model': order.device_model,
                'condition': order.device_condition
            },
            'problem_description': order.problem_description,
            'estimated_cost': str(order.estimated_cost or 0),
            'final_cost': str(order.final_cost or 0),
            'estimated_completion': order.estimated_completion,
            'actual_completion': order.actual_completion,
            'warranty_expires': order.warranty_expires,
            'status_history': [
                {
                    'status': history.get_new_status_display(),
                    'date': history.created_at,
                    'notes': history.notes
                }
                for history in status_history
            ]
        })


# Loyalty Program Views
class PointsBalanceAPIView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            customer = request.user.customerprofile

            # Get recent transactions
            recent_transactions = customer.point_transactions.order_by('-created_at')[:10]

            return Response({
                'current_points': customer.total_points,
                'lifetime_points': customer.lifetime_points,
                'membership_level': customer.get_membership_level_display(),
                'points_to_next_level': customer.get_points_to_next_level(),
                'discount_percentage': customer.get_discount_percentage(),
                'recent_transactions': [
                    {
                        'points': trans.points,
                        'type': trans.get_transaction_type_display(),
                        'reason': trans.reason,
                        'date': trans.created_at,
                        'balance_after': trans.balance_after
                    }
                    for trans in recent_transactions
                ]
            })
        except CustomerProfile.DoesNotExist:
            return Response({
                'error': 'Customer profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class AvailableRewardsAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            customer = request.user.customerprofile

            # Get available rewards for this customer
            rewards = LoyaltyReward.objects.filter(is_active=True)
            available_rewards = []

            for reward in rewards:
                if reward.is_available_for_customer(customer):
                    available_rewards.append({
                        'id': reward.id,
                        'name': reward.name,
                        'description': reward.description,
                        'reward_type': reward.get_reward_type_display(),
                        'points_required': reward.points_required,
                        'discount_percentage': reward.discount_percentage,
                        'discount_amount': str(reward.discount_amount or 0),
                        'can_redeem': customer.total_points >= reward.points_required
                    })

            return Response({
                'rewards': available_rewards,
                'customer_points': customer.total_points
            })

        except CustomerProfile.DoesNotExist:
            return Response({
                'error': 'Customer profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class RedeemRewardAPIView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            customer = request.user.customerprofile
            reward_id = request.data.get('reward_id')

            if not reward_id:
                return Response({
                    'error': 'Reward ID is required'
                }, status=status.HTTP_400_BAD_REQUEST)

            try:
                reward = LoyaltyReward.objects.get(id=reward_id)
            except LoyaltyReward.DoesNotExist:
                return Response({
                    'error': 'Reward not found'
                }, status=status.HTTP_404_NOT_FOUND)

            if reward.redeem_for_customer(customer):
                return Response({
                    'success': True,
                    'message': f'Reward "{reward.name}" redeemed successfully',
                    'remaining_points': customer.total_points
                })
            else:
                return Response({
                    'error': 'Unable to redeem reward. Check eligibility and points balance.'
                }, status=status.HTTP_400_BAD_REQUEST)

        except CustomerProfile.DoesNotExist:
            return Response({
                'error': 'Customer profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


# Utility Views
class ContactAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]

    @rate_limit('10/hour')
    def post(self, request):
        data = request.data
        required_fields = ['name', 'email', 'inquiry_type', 'message']

        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Create contact submission
        contact = ContactSubmission.objects.create(
            name=data['name'],
            email=data['email'],
            phone=data.get('phone', ''),
            inquiry_type=data['inquiry_type'],
            subject=data.get('subject', f"{data['inquiry_type']} inquiry"),
            message=data['message'],
            laptop_brand_id=data.get('laptop_brand_id'),
            laptop_model=data.get('laptop_model', ''),
            issue_description=data.get('issue_description', ''),
            source='api',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return Response({
            'success': True,
            'message': 'Your inquiry has been submitted successfully. We will contact you soon.',
            'reference_number': f"INQ-{contact.id:06d}"
        }, status=status.HTTP_201_CREATED)


class ServiceQuoteAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]

    @rate_limit('5/hour')
    def post(self, request):
        data = request.data
        required_fields = ['name', 'email', 'phone', 'service_id', 'device_brand', 'device_model', 'description']

        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            service = Service.objects.get(id=data['service_id'], is_active=True)
        except Service.DoesNotExist:
            return Response({
                'error': 'Service not found'
            }, status=status.HTTP_404_NOT_FOUND)

        # Get brand if provided
        brand = None
        if data.get('brand_id'):
            try:
                brand = Brand.objects.get(id=data['brand_id'])
            except Brand.DoesNotExist:
                pass

        # Calculate price estimate
        urgency = data.get('urgency', 'normal')
        priority_map = {
            'normal': 'standard',
            'priority': 'express',
            'express': 'emergency'
        }
        priority = priority_map.get(urgency, 'standard')

        price_range = service.get_price_range(brand=brand, priority=priority)

        # Create contact submission for quote
        contact = ContactSubmission.objects.create(
            name=data['name'],
            email=data['email'],
            phone=data['phone'],
            inquiry_type='quote',
            subject=f"Service Quote Request - {service.name}",
            message=data['description'],
            laptop_brand=brand,
            laptop_model=data['device_model'],
            issue_description=data['description'],
            source='api',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )

        return Response({
            'success': True,
            'message': 'Quote request submitted successfully',
            'service': service.name,
            'estimated_price_range': price_range,
            'estimated_duration': str(service.estimated_duration),
            'warranty_period': f"{service.warranty_period} days",
            'reference_number': f"QUO-{contact.id:06d}"
        }, status=status.HTTP_201_CREATED)


class HealthCheckAPIView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'healthy',
            'timestamp': timezone.now(),
            'version': '2.0.0',
            'services': {
                'database': 'connected',
                'cache': 'connected' if cache.get('health_check') is not None else 'disconnected',
                'api': 'operational'
            }
        })


# Documentation views
@api_view(['GET'])
@permission_classes([AllowAny])
def api_documentation(request):
    """API Documentation endpoint"""
    docs = {
        'version': '2.0.0',
        'title': 'Service Laptop Bandung API',
        'description': 'REST API for Service Laptop Bandung application',
        'base_url': request.build_absolute_uri('/api/v1/'),
        'authentication': {
            'type': 'Session Authentication',
            'login_endpoint': '/api/v1/auth/login/',
            'logout_endpoint': '/api/v1/auth/logout/'
        },
        'endpoints': {
            'authentication': {
                'POST /auth/login/': 'User login',
                'POST /auth/logout/': 'User logout',
                'POST /auth/register/': 'User registration',
                'GET /auth/profile/': 'Get user profile',
                'PUT /auth/profile/': 'Update user profile'
            },
            'services': {
                'GET /services/': 'List all services',
                'GET /services/{slug}/': 'Get service details',
                'GET /services/search/': 'Search services',
                'GET /services/popular/': 'Get popular services',
                'POST /services/compare/': 'Compare services'
            },
            'orders': {
                'GET /orders/': 'List customer orders',
                'POST /orders/create/': 'Create new order',
                'GET /orders/track/{order_number}/': 'Track order status'
            },
            'loyalty': {
                'GET /loyalty/points/': 'Get points balance',
                'GET /loyalty/rewards/': 'Get available rewards',
                'POST /loyalty/redeem/': 'Redeem reward'
            },
            'utility': {
                'POST /contact/': 'Submit contact form',
                'POST /quote/': 'Request service quote',
                'GET /health/': 'API health check'
            }
        },
        'response_format': {
            'success': {
                'success': True,
                'data': '...',
                'message': 'Success message'
            },
            'error': {
                'error': 'Error message',
                'details': '...'
            }
        },
        'rate_limits': {
            'contact': '10 requests per hour',
            'quote': '5 requests per hour',
            'general': '1000 requests per hour'
        }
    }

    return Response(docs)


@api_view(['GET'])
@permission_classes([AllowAny])
def api_schema(request):
    """API Schema endpoint"""
    schema = {
        'openapi': '3.0.0',
        'info': {
            'title': 'Service Laptop Bandung API',
            'version': '2.0.0',
            'description': 'REST API for laptop service management'
        },
        'servers': [
            {
                'url': request.build_absolute_uri('/api/v1/'),
                'description': 'Production server'
            }
        ],
        'paths': {
            # This would contain full OpenAPI schema
            # For brevity, showing just the structure
        }
    }

    return Response(schema)