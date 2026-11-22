from django.db import models

# Create your models here.
from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Append-only record of important actions (moderation, uploads)."""
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=60)
    target_type = models.CharField(max_length=60, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["action", "-created_at"])]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.target_type}:{self.target_id}"
