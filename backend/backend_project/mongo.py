"""
MongoDB connection and helper utilities for Civility.ai
"""

import os
from pymongo import MongoClient
from datetime import datetime, timezone
from django.conf import settings


_client = None
_db = None


def get_db():
    """Get MongoDB database instance (singleton)."""
    global _client, _db
    if _db is None:
        uri = getattr(settings, 'MONGODB_URI', 'mongodb://localhost:27017/')
        db_name = getattr(settings, 'MONGODB_NAME', 'civility_ai')
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        _db = _client[db_name]
    return _db


def get_collection(name):
    """Get a MongoDB collection by name."""
    return get_db()[name]


# ── User operations ──────────────────────────────────────────

def find_user_by_email(email):
    """Find a user by their email address."""
    return get_collection('users').find_one({'email': email})


def find_user_by_id(user_id):
    """Find a user by their user_id."""
    return get_collection('users').find_one({'user_id': user_id})


def create_or_update_user(user_data):
    """Create or update a user document in MongoDB."""
    collection = get_collection('users')
    existing = collection.find_one({'email': user_data['email']})

    if existing:
        collection.update_one(
            {'email': user_data['email']},
            {'$set': {
                'name': user_data.get('name', existing.get('name', '')),
                'picture': user_data.get('picture', existing.get('picture', '')),
                'last_login': datetime.now(timezone.utc),
            }}
        )
        return collection.find_one({'email': user_data['email']})
    else:
        new_user = {
            'user_id': user_data.get('user_id', user_data['email']),
            'email': user_data['email'],
            'name': user_data.get('name', ''),
            'picture': user_data.get('picture', ''),
            'created_at': datetime.now(timezone.utc),
            'last_login': datetime.now(timezone.utc),
            'total_uploads': 0,
            'flagged_count': 0,
            'consecutive_flagged': 0,
            'abuse_score': 0,
            'behavior_category': 'Safe',
            'status': 'active',  # active | suspended
        }
        collection.insert_one(new_user)
        return new_user


# ── Moderation logs ─────────────────────────────────────────

def save_moderation_log(log_data):
    """Save a content moderation result to MongoDB."""
    log_data['created_at'] = datetime.now(timezone.utc)
    return get_collection('moderation_logs').insert_one(log_data)


def get_user_moderation_logs(user_id, limit=50):
    """Get moderation logs for a specific user."""
    return list(
        get_collection('moderation_logs')
        .find({'user_id': user_id})
        .sort('created_at', -1)
        .limit(limit)
    )


# ── Behavior tracking ───────────────────────────────────────

def update_user_behavior(user_id, is_flagged, abusive_score):
    """Update user behavior stats after moderation."""
    collection = get_collection('users')
    user = collection.find_one({'user_id': user_id})

    if not user:
        return None

    total_uploads = user.get('total_uploads', 0) + 1
    flagged_count = user.get('flagged_count', 0) + (1 if is_flagged else 0)

    # Consecutive flagged counter (for repeat-offender detection)
    if is_flagged:
        consecutive_flagged = user.get('consecutive_flagged', 0) + 1
    else:
        consecutive_flagged = 0

    # Calculate rolling abuse score (weighted average)
    current_abuse = user.get('abuse_score', 0)
    new_abuse = round((current_abuse * 0.7) + (abusive_score * 0.3), 1)

    # Determine behavior category
    if new_abuse < 20:
        category = 'Safe'
    elif new_abuse < 45:
        category = 'Warning'
    elif new_abuse < 70:
        category = 'Risky'
    else:
        category = 'Critical'

    collection.update_one(
        {'user_id': user_id},
        {'$set': {
            'total_uploads': total_uploads,
            'flagged_count': flagged_count,
            'consecutive_flagged': consecutive_flagged,
            'abuse_score': new_abuse,
            'behavior_category': category,
        }}
    )

    return {
        'total_uploads': total_uploads,
        'flagged_count': flagged_count,
        'consecutive_flagged': consecutive_flagged,
        'abuse_score': new_abuse,
        'behavior_category': category,
    }


def get_user_behavior(user_id):
    """Get behavior data for a specific user."""
    user = get_collection('users').find_one({'user_id': user_id})
    if not user:
        return None
    return {
        'user_id': user.get('user_id'),
        'email': user.get('email'),
        'name': user.get('name'),
        'total_uploads': user.get('total_uploads', 0),
        'flagged_count': user.get('flagged_count', 0),
        'abuse_score': user.get('abuse_score', 0),
        'behavior_category': user.get('behavior_category', 'Safe'),
    }
