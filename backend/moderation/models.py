from django.db import models


class Content(models.Model):
    text = models.TextField()
    flagged_count = models.IntegerField()
    score = models.FloatField()
    user_email = models.EmailField()

    def __str__(self):
        return self.text[:50]
