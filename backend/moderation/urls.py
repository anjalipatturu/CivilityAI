from django.urls import path
from .views import test_content


urlpatterns = [
    path('test/', test_content),
]
