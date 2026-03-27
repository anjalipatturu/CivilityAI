"""Utility helpers for Civility.ai backend"""

import os
import tempfile
import uuid
from django.core.mail import send_mail
from django.conf import settings


def save_uploaded_file(uploaded_file):
    """
    Save an uploaded file to a temporary directory.
    Returns the full file path.
    """
    temp_dir = tempfile.mkdtemp(prefix='civility_upload_')
    file_path = os.path.join(temp_dir, uploaded_file.name)

    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    return file_path


def cleanup_file(file_path):
    """Clean up a temporary file."""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            parent_dir = os.path.dirname(file_path)
            if os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                os.rmdir(parent_dir)
    except OSError:
        pass


def blur_image_to_media(temp_path, original_filename):
    """Blur an image and save it under MEDIA_ROOT/blurred.

    Returns the web-accessible URL (using MEDIA_URL) or None on failure.
    """
    try:
        from PIL import Image, ImageFilter
    except Exception:
        return None

    try:
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        if not media_root:
            return None

        blurred_dir = os.path.join(media_root, 'blurred')
        os.makedirs(blurred_dir, exist_ok=True)

        base, ext = os.path.splitext(original_filename or 'image.jpg')
        ext = ext or '.jpg'
        filename = f"{uuid.uuid4().hex}{ext}"
        out_path = os.path.join(blurred_dir, filename)

        with Image.open(temp_path) as img:
            blurred = img.filter(ImageFilter.GaussianBlur(radius=20))
            blurred.save(out_path)

        # Build URL (MEDIA_URL already ends with '/media/')
        if not media_url.endswith('/'):
            media_url = media_url + '/'
        return f"{media_url}blurred/{filename}"
    except Exception:
        return None


def get_content_type_from_file(file_name):
    """Determine content type from file extension."""
    ext = os.path.splitext(file_name)[1].lower()
    image_exts = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'}
    video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    audio_exts = {'.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac', '.webm'}

    if ext in image_exts:
        return 'image'
    elif ext in video_exts:
        return 'video'
    elif ext in audio_exts:
        return 'audio'
    else:
        return 'unknown'


def send_admin_alert(user_data, reason='Repeated abuse violations'):
    """
    Send an alert email to the admin about a problematic user.
    """
    admin_email = getattr(settings, 'ADMIN_EMAIL', 'admin@civility.ai')

    subject = f'⚠️ Civility.ai Alert: User {user_data.get("email", "unknown")} - {user_data.get("behavior_category", "Warning")}'

    message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 Civility.ai Admin Alert
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User Information:
  • Email: {user_data.get('email', 'N/A')}
  • Name: {user_data.get('name', 'N/A')}
  • User ID: {user_data.get('user_id', 'N/A')}

Behavior Metrics:
  • Abuse Score: {user_data.get('abuse_score', 0)}/100
  • Behavior Category: {user_data.get('behavior_category', 'Unknown')}
  • Total Uploads: {user_data.get('total_uploads', 0)}
  • Flagged Count: {user_data.get('flagged_count', 0)}

Reason: {reason}

Action Required: Please review this user's activity.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    try:
        # Use the configured SMTP sender address so providers like Gmail
        # accept and deliver the message correctly.
        from_email = getattr(settings, 'EMAIL_HOST_USER', 'noreply@civility.ai')

        sent_count = send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[admin_email],
            fail_silently=True,
        )

        # Log a hint to the console if no messages were accepted by
        # the SMTP server so configuration issues are visible.
        if sent_count == 0:
            print("[Civility.ai] Admin alert email not sent; check EMAIL_HOST_USER/EMAIL_HOST_PASSWORD/ADMIN_EMAIL settings.")
            return False

        return True
    except Exception:
        # Log the alert to console as fallback
        print(f"\n{'='*50}")
        print(message)
        print(f"{'='*50}\n")
        return False


def send_user_email(email, subject, message):
    """Low-level helper to send a plain-text email to a user."""
    if not email:
        return False

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@civility.ai',
            recipient_list=[email],
            fail_silently=True,
        )
        return True
    except Exception:
        return False


def send_user_warning_email(email, abuse_score):
    """CASE 2 warning email: mild inappropriate behavior."""
    subject = 'Civility.ai: Please maintain respectful communication'
    message = (
        'Your recent activity appears potentially inappropriate or '
        f'borderline toxic (abuse score: {abuse_score}). Please maintain '
        'respectful communication to keep our community safe.'
    )
    return send_user_email(email, subject, message)


def send_user_violation_email(email, abuse_score, action):
    """CASE 3/4 violation email: content removed or account suspended."""
    if action == 'delete_post':
        subject = 'Civility.ai: Your content was removed'
        message = (
            'Your recent content violated our guidelines and has been '
            f'removed (abuse score: {abuse_score}). Continued violations '
            'may result in account suspension.'
        )
    elif action == 'delete_account':
        subject = 'Civility.ai: Your account has been removed'
        message = (
            'Due to severe policy violations (abuse score: '
            f'{abuse_score}), your account has been removed.'
        )
    else:
        return False

    return send_user_email(email, subject, message)


def send_admin_alert_email(user_data, reason):
    """Thin wrapper for admin alerts to satisfy the spec naming."""
    return send_admin_alert(user_data, reason=reason)
