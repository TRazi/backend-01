"""
Celery Configuration for KinWise Backend

Django Best Practice: Separate Celery configuration with auto-discovery,
task routes for organization, and beat schedule for periodic tasks.
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("kinwise")

# Load settings from Django
# namespace='CELERY' means all celery-related settings keys should have a `CELERY_` prefix
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks from all installed apps
# This will look for tasks.py in each installed app
app.autodiscover_tasks()

# Periodic tasks configuration
# Django Best Practice: Define schedules centrally for maintainability
app.conf.beat_schedule = {
    "send-bill-reminders-daily": {
        "task": "bills.tasks.send_bill_reminders",
        "schedule": crontab(hour=9, minute=0),  # 9 AM daily
    },
    "check-goal-milestones-daily": {
        "task": "goals.tasks.check_goal_milestones",
        "schedule": crontab(hour=10, minute=0),  # 10 AM daily
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Debug task for testing Celery setup.

    Usage:
        python manage.py shell
        >>> from config.celery import debug_task
        >>> result = debug_task.delay()
        >>> result.status
    """
    print(f"Request: {self.request!r}")
    return "Debug task executed successfully"
