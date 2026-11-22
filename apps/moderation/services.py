"""Moderation rules live here, not in views, so they are easy to test."""
from django.conf import settings
from django.utils import timezone

from apps.core import audit
from apps.resources.models import Resource


class ModerationError(Exception):
    """Raised with a message that is safe to show to the moderator."""


def _require_state(resource, allowed, action):
    if resource.status not in allowed:
        raise ModerationError(f"A resource that is {resource.get_status_display().lower()} cannot be {action}.")


def can_approve(resource):
    """Approve only files that passed the scan. The one exception is development
    mode, where no scanner may be installed (ALLOW_APPROVE_WITHOUT_SCAN)."""
    if not resource.file:
        return False
    if resource.scan_status == Resource.ScanStatus.CLEAN:
        return True
    return settings.ALLOW_APPROVE_WITHOUT_SCAN and resource.scan_status in (
        Resource.ScanStatus.UNAVAILABLE, Resource.ScanStatus.PENDING)


def approve(resource, moderator):
    _require_state(resource, [Resource.Status.PENDING], "approved")
    if not can_approve(resource):
        raise ModerationError("This file has not passed the security scan, so it cannot be approved yet. "
                              "Run the scan again once the scanner is available.")
    resource.status = Resource.Status.APPROVED
    resource.rejection_reason = ""
    resource.reviewed_by, resource.reviewed_at = moderator, timezone.now()
    resource.save(update_fields=["status", "rejection_reason", "reviewed_by", "reviewed_at"])
    audit.record(moderator, "resource.approve", resource, resource.title)


def reject(resource, moderator, reason):
    reason = (reason or "").strip()
    if len(reason) < 5:
        raise ModerationError("Please give a reason of at least a few words so the uploader knows what to fix.")
    _require_state(resource, [Resource.Status.PENDING, Resource.Status.HIDDEN, Resource.Status.APPROVED], "rejected")
    resource.status = Resource.Status.REJECTED
    resource.rejection_reason = reason[:500]
    resource.reviewed_by, resource.reviewed_at = moderator, timezone.now()
    resource.save(update_fields=["status", "rejection_reason", "reviewed_by", "reviewed_at"])
    audit.record(moderator, "resource.reject", resource, reason)


def hide(resource, moderator):
    _require_state(resource, [Resource.Status.APPROVED], "hidden")
    resource.status = Resource.Status.HIDDEN
    resource.reviewed_by, resource.reviewed_at = moderator, timezone.now()
    resource.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    audit.record(moderator, "resource.hide", resource, resource.title)


def restore(resource, moderator):
    _require_state(resource, [Resource.Status.HIDDEN], "restored")
    resource.status = Resource.Status.APPROVED
    resource.reviewed_by, resource.reviewed_at = moderator, timezone.now()
    resource.save(update_fields=["status", "reviewed_by", "reviewed_at"])
    audit.record(moderator, "resource.restore", resource, resource.title)
