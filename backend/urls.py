from django.urls import path, include

urlpatterns = [
    # Delegate all routes to the main project URL configuration
    path('', include('backend_project.urls')),
]
