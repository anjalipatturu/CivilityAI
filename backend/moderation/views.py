from django.http import JsonResponse

from .models import Content


def test_content(request):
    """Simple test view to create a Content entry and trigger the signal.

    Hitting this endpoint will create a Content object with flagged_count=3
    and score=80, which should cause an admin alert email to be sent via the
    post_save signal in moderation/signals.py.
    """
    Content.objects.create(
        text="This is harmful content",
        flagged_count=3,
        score=80,
        user_email="user@gmail.com",
    )

    return JsonResponse({"message": "Content created & checked!"})
