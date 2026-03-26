"""WSGI config for the Civility.ai backend project.

This exposes the WSGI callable as a module-level variable named ``application``.
It is used by Django's development server and any WSGI-capable production server.
"""

import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend_project.settings")

application = get_wsgi_application()
