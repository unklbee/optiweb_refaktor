# customers/urls.py
"""
Enhanced customer URLs with better organization
"""

from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

app_name = 'customers'

# Authentication patterns
auth_patterns = [
    path('login/', auth_views.LoginView.as_view(
        template_name='customers/login.html',
        redirect_authenticated_user=True,
        extra_context={'page_title': 'Login Customer - Service Laptop Bandung'}
    ), name='login'),

    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    path('register/', views.CustomerRegistrationView.as_view(), name='register'),

    # Password reset flow
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='customers/password_reset.html',
        email_template_name='customers/password_reset_email.html',
        subject_template_name='customers/password_reset_subject.txt',
        extra_context={'page_title': 'Reset Password'}
    ), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='customers/password_reset_done.html'
    ), name='password_reset_done'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='customers/password_reset_confirm.html'
    ), name='password_reset_confirm'),

    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='customers/password_reset_complete.html'
    ), name='password_reset_complete'),

    # Email verification
    path('verify-email/<str:token>/', views.EmailVerificationView.as_view(), name='verify_email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend_verification'),
]

# Dashboard patterns
dashboard_patterns = [
    path('', views.CustomerDashboardView.as_view(), name='dashboard'),
    path('profile/', views.ProfileUpdateView.as_view(), name='profile'),
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
    path('settings/', views.CustomerSettingsView.as_view(), name='settings'),
]

# Order patterns
order_patterns = [
    path('', views.CustomerOrderListView.as_view(), name='orders'),
    path('create/', views.CreateOrderView.as_view(), name='create_order'),
    path('<str:order_number>/', views.OrderDetailView.as_view(), name='order_detail'),
    path('<str:order_number>/cancel/', views.CancelOrderView.as_view(), name='cancel_order'),
    path('<str:order_number>/review/', views.SubmitReviewView.as_view(), name='submit_review'),
]

# Loyalty patterns
loyalty_patterns = [
    path('', views.LoyaltyProgramView.as_view(), name='loyalty'),
    path('rewards/', views.AvailableRewardsView.as_view(), name='rewards'),
    path('rewards/<int:reward_id>/redeem/', views.RedeemRewardView.as_view(), name='redeem_reward'),
    path('redemptions/', views.RedemptionHistoryView.as_view(), name='redemption_history'),
    path('points/history/', views.PointHistoryView.as_view(), name='point_history'),
]

# AJAX API patterns
ajax_patterns = [
    path('order-status/<str:order_number>/', views.check_order_status_ajax, name='check_order_status'),
    path('service-price/<int:service_id>/', views.get_service_price_ajax, name='get_service_price'),
    path('redeem-reward/<int:reward_id>/', views.redeem_reward_ajax, name='redeem_reward_ajax'),
    path('submit-review/<int:order_id>/', views.submit_review_ajax, name='submit_review_ajax'),
    path('update-preferences/', views.update_preferences_ajax, name='update_preferences'),
    path('check-referral/<str:code>/', views.check_referral_code_ajax, name='check_referral'),
]

urlpatterns = [
    # Authentication
    path('', include(auth_patterns)),

    # Dashboard (requires authentication)
    path('dashboard/', include(dashboard_patterns)),

    # Orders
    path('orders/', include(order_patterns)),

    # Loyalty program
    path('loyalty/', include(loyalty_patterns)),

    # AJAX endpoints
    path('ajax/', include(ajax_patterns)),
]
