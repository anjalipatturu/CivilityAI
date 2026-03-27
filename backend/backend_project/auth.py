"""
OAuth 2.0 Authentication module for Civility.ai
Handles Google OAuth token verification & JWT generation
"""

import datetime

import jwt
import requests
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .mongo import create_or_update_user, find_user_by_email, find_user_by_id, get_collection


def _fetch_google_userinfo_with_access_token(access_token):
    """Resolve a Google OAuth access token into user info.

    Tries both the OpenID userinfo endpoint (v3) and the
    OAuth2 userinfo endpoint (v2) to be robust against
    different scope configurations.
    """

    # Try OpenID Connect userinfo endpoint (requires "openid" scope)
    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v3/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=5,
        )

        if response.status_code == 200:
            data = response.json()
            user_id = data.get('sub')
            email = data.get('email')
            if user_id and email:
                return {
                    'user_id': user_id,
                    'email': email,
                    'name': data.get('name', ''),
                    'picture': data.get('picture', ''),
                }
    except Exception:
        # Fall through to the v2 endpoint below
        pass

    # Fallback: older OAuth2 userinfo endpoint (works with profile/email scopes)
    try:
        response = requests.get(
            'https://www.googleapis.com/oauth2/v2/userinfo',
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=5,
        )

        if response.status_code != 200:
            return None

        data = response.json()
        user_id = data.get('id') or data.get('sub')
        email = data.get('email')
        if not user_id or not email:
            return None

        return {
            'user_id': user_id,
            'email': email,
            'name': data.get('name', ''),
            'picture': data.get('picture', ''),
        }
    except Exception:
        return None


def verify_google_token(token):
    """Verify a Google token (access token or ID token).

    Returns user info dict on success, or None on failure.
    """
    try:
        client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '').strip()

        # If no client ID is configured or it's still the placeholder
        # from the example .env, fall back to demo mode so development
        # and "Demo" login work without real Google credentials.
        if not client_id or client_id.startswith('your-google-client-id'):
            return _demo_verify(token)

        # 1) First, assume we were given an OAuth access token and try userinfo.
        userinfo = _fetch_google_userinfo_with_access_token(token)
        if userinfo:
            return userinfo

        # 2) If that fails, fall back to verifying an ID token.
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


def register_local_user(email, password, name=''):
    """Register a local (email/password) user.

    Returns (result, error) similar to login_with_google.
    """

    email = (email or '').strip().lower()
    if not email or not password:
        return None, 'Email and password are required'

    existing = find_user_by_email(email)
    if existing and existing.get('password_hash'):
        return None, 'User with this email already exists'

    # Base user info; user_id defaults to email for local accounts
    user_info = {
        'user_id': existing.get('user_id') if existing else email,
        'email': email,
        'name': name or existing.get('name', '') if existing else name or '',
        'picture': existing.get('picture', '') if existing else '',
    }

    # Create or update the user document
    create_or_update_user(user_info)

    # Store password hash separately
    users = get_collection('users')
    users.update_one(
        {'email': email},
        {'$set': {'password_hash': make_password(password)}},
    )

    created = find_user_by_email(email)
    user_payload = {
        'user_id': created.get('user_id', email),
        'email': created.get('email', email),
        'name': created.get('name', ''),
        'picture': created.get('picture', ''),
    }

    jwt_token = generate_jwt(user_payload)

    return {
        'token': jwt_token,
        'user': user_payload,
    }, None


def login_with_password(email, password):
    """Authenticate a user via email/password.

    Returns (result, error) similar to login_with_google.
    """

    email = (email or '').strip().lower()
    if not email or not password:
        return None, 'Email and password are required'

    user = find_user_by_email(email)
    if not user or not user.get('password_hash'):
        return None, 'Invalid email or password'

    if not check_password(password, user['password_hash']):
        return None, 'Invalid email or password'

    user_payload = {
        'user_id': user.get('user_id', email),
        'email': user.get('email', email),
        'name': user.get('name', ''),
        'picture': user.get('picture', ''),
    }

    jwt_token = generate_jwt(user_payload)

    # Update last_login timestamp
    users = get_collection('users')
    users.update_one(
        {'email': email},
        {'$set': {'last_login': datetime.datetime.now(datetime.timezone.utc)}},
    )

    return {
        'token': jwt_token,
        'user': user_payload,
    }, None
