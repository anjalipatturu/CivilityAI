"""
URL Configuration for Civility.ai backend
"""

from django.urls import path
from . import views

urlpatterns = [
    # Health check
    path('', views.health_check, name='health_check'),
    path('api/health', views.health_check, name='api_health'),

    # Authentication
    path('auth/google-login', views.google_login, name='google_login'),
    path('auth/verify', views.verify_token, name='verify_token'),

    # Content moderation
    path('analyze-content', views.analyze_content, name='analyze_content'),

    # User behavior
    path('user-behavior', views.user_behavior, name='user_behavior'),

    # Admin alerts
    path('send-alert', views.send_alert, name='send_alert'),

    # Moderation history
    path('moderation-history', views.moderation_history, name='moderation_history'),
]
