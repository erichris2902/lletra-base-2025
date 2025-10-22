import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ikigai2025.settings")

app = Celery("ikigai2025")

app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks.py en tus apps
app.autodiscover_tasks()