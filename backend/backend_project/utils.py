"""
Utility helpers for Civility.ai backend
"""

import os
import tempfile
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
        send_mail(
            subject=subject,
            message=message,
            from_email='noreply@civility.ai',
            recipient_list=[admin_email],
            fail_silently=True,
        )
        return True
    except Exception:
        # Log the alert to console as fallback
        print(f"\n{'='*50}")
        print(message)
        print(f"{'='*50}\n")
        return False
