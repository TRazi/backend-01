# apps/common/models.py
from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base class model that provides self-updating timestamps.
    created_at: DateTime when the object was created.
    updated_at: DateTime when the object was last modified.
    """

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
