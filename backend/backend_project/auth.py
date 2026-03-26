"""
OAuth 2.0 Authentication module for Civility.ai
Handles Google OAuth token verification & JWT generation
"""

import jwt
import datetime
from django.conf import settings
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .mongo import create_or_update_user, find_user_by_id


def verify_google_token(token):
    """
    Verify a Google OAuth ID token.
    Returns user info if valid, None if invalid.
    """
    try:
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')

        if not client_id:
            # Demo mode — accept the token as-is (for development)
            return _demo_verify(token)

        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id,
        )

        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            return None

        return {
            'user_id': idinfo['sub'],
            'email': idinfo['email'],
            'name': idinfo.get('name', ''),
            'picture': idinfo.get('picture', ''),
        }

    except ValueError:
        return None
    except Exception:
        return None


def _demo_verify(token):
    """
    Demo verification for development without Google OAuth credentials.
    Accepts any token and returns demo user data.
    """
    return {
        'user_id': 'demo_user_001',
        'email': 'demo@civility.ai',
        'name': 'Demo User',
        'picture': '',
    }


def generate_jwt(user_data):
    """Generate a JWT token for the authenticated user."""
    payload = {
        'user_id': user_data['user_id'],
        'email': user_data['email'],
        'name': user_data.get('name', ''),
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(
            hours=getattr(settings, 'JWT_EXPIRATION_HOURS', 24)
        ),
        'iat': datetime.datetime.now(datetime.timezone.utc),
    }

    return jwt.encode(
        payload,
        getattr(settings, 'JWT_SECRET', 'secret'),
        algorithm=getattr(settings, 'JWT_ALGORITHM', 'HS256'),
    )


def verify_jwt(token):
    """Verify a JWT token and return the payload."""
    try:
        payload = jwt.decode(
            token,
            getattr(settings, 'JWT_SECRET', 'secret'),
            algorithms=[getattr(settings, 'JWT_ALGORITHM', 'HS256')],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_from_request(request):
    """
    Extract and verify the JWT from request Authorization header.
    Returns user_id if valid, None otherwise.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')

    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]
    payload = verify_jwt(token)

    if payload:
        return payload.get('user_id')

    return None


def login_with_google(google_token):
    """
    Full Google login flow:
    1. Verify Google token
    2. Create/update user in MongoDB
    3. Generate JWT
    """
    user_info = verify_google_token(google_token)

    if not user_info:
        return None, 'Invalid Google token'

    # Store / update user in MongoDB
    user = create_or_update_user(user_info)

    # Generate JWT for the session
    jwt_token = generate_jwt(user_info)

    return {
        'token': jwt_token,
        'user': {
            'user_id': user_info['user_id'],
            'email': user_info['email'],
            'name': user_info.get('name', ''),
            'picture': user_info.get('picture', ''),
        }
    }, None
