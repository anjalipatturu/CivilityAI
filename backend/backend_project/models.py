"""
MongoDB document models for Civility.ai
These are schema definitions (not Django ORM models).
MongoDB is schema-less, but these serve as documentation and validation helpers.
"""

from datetime import datetime, timezone


def user_document(user_id, email, name='', picture=''):
    """Create a new user document schema."""
    return {
        'user_id': user_id,
        'email': email,
        'name': name,
        'picture': picture,
        'created_at': datetime.now(timezone.utc),
        'last_login': datetime.now(timezone.utc),
        'total_uploads': 0,
        'flagged_count': 0,
        'abuse_score': 0,
        'behavior_category': 'Safe',
    }


def moderation_log_document(user_id, content_type, status, reason,
                            confidence_score, abusive_score,
                            categories_detected=None,
                            corrected_text=None,
                            transcribed_text=None,
                            original_filename=None):
    """Create a moderation log document schema."""
    return {
        'user_id': user_id,
        'content_type': content_type,
        'status': status,
        'reason': reason,
        'confidence_score': confidence_score,
        'abusive_score': abusive_score,
        'categories_detected': categories_detected or [],
        'corrected_text': corrected_text,
        'transcribed_text': transcribed_text,
        'original_filename': original_filename,
        'created_at': datetime.now(timezone.utc),
    }


def alert_document(user_id, user_email, abuse_score, behavior_category, reason):
    """Create an alert document schema."""
    return {
        'user_id': user_id,
        'user_email': user_email,
        'abuse_score': abuse_score,
        'behavior_category': behavior_category,
        'reason': reason,
        'sent_at': datetime.now(timezone.utc),
        'acknowledged': False,
    }
