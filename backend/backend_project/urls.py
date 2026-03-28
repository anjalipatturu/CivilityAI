"""URL Configuration for Civility.ai backend"""

from django.urls import path
from . import views
from moderation.views import test_content

urlpatterns = [
    # Health check
    path('', views.health_check, name='health_check'),
    path('api/health', views.health_check, name='api_health'),

    # Debug: download last audio
    path('debug/download-last-audio', views.download_last_audio, name='download_last_audio'),

    # Favicon (prevent 404 noise)
    path('favicon.ico', views.favicon, name='favicon'),

    # Authentication
    path('auth/register', views.email_register, name='email_register'),
    path('auth/login', views.email_login, name='email_login'),
    path('auth/google-login', views.google_login, name='google_login'),
    path('auth/verify', views.verify_token, name='verify_token'),

    # Content moderation
    path('analyze-content', views.analyze_content, name='analyze_content'),

    # Audio transcription (voice-to-text helper)
    path('transcribe-audio', views.transcribe_audio, name='transcribe_audio'),

    # Simple Speech-to-Text (DRF view)
    path('speech-to-text', views.speech_to_text, name='speech_to_text'),
    path('api/speech-to-text/', views.speech_to_text, name='api_speech_to_text'),

    # User behavior
    path('user-behavior', views.user_behavior, name='user_behavior'),

    # Admin alerts
    path('send-alert', views.send_alert, name='send_alert'),

    # Moderation history
    path('moderation-history', views.moderation_history, name='moderation_history'),

    # Test endpoint to trigger Content signal-based admin email
    path('test-content', test_content, name='test_content'),

    # Alternate test route
    path('test/', test_content),
]
