"""
Django Configuration Package

Django Best Practice: Import Celery app when Django starts to ensure
it's always imported when Django starts so that shared_task will use this app.
"""

# This will make sure the app is always imported when Django starts
# so that shared_task will use this app.
from .celery import app as celery_app

__all__ = ("celery_app",)
