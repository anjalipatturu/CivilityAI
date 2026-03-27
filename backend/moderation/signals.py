from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings

from .models import Content


def send_admin_alert(instance):
    subject = "⚠️ Content Moderation Alert"

    message = f"""
Alert!

A user has posted content that crossed moderation limits.

🔹 User Email: {instance.user_email}
🔹 Flagged Count: {instance.flagged_count}
🔹 Toxicity Score: {instance.score}%

🔹 Content:
{instance.text}

Please review this content immediately.
"""

    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [settings.ADMIN_EMAIL],
        fail_silently=False,
    )


@receiver(post_save, sender=Content)
def moderation_check(sender, instance, created, **kwargs):
    if instance.flagged_count >= 3 or instance.score >= 75:
        send_admin_alert(instance)
