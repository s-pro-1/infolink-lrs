import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core import audit

from .models import Resource, ResourceTag
from .scanning import scan_resource


def uploads_in_last_hour(user):
    return Resource.objects.filter(uploader=user, created_at__gte=timezone.now() - timedelta(hours=1)).count()


def over_upload_limit(user):
    return uploads_in_last_hour(user) >= settings.UPLOADS_PER_HOUR


def parse_tags(text):
    """'Python, Exam 2023,, python' -> ['python', 'exam 2023']  (max 8, 30 chars each)."""
    seen, out = set(), []
    for raw in re.split(r"[,\n]", text or ""):
        tag = re.sub(r"\s+", " ", raw).strip().lower()[:30]
        if tag and tag not in seen:
            seen.add(tag)
            out.append(tag)
    return out[:8]


def title_from_filename(name):
    stem = name.rsplit(".", 1)[0]
    return re.sub(r"[_\-]+", " ", stem).strip()[:200] or "Untitled"


def create_resource(*, user, uploaded, validated, title, description, course, category, tags):
    """Store a validated upload as a PENDING resource, then scan it.

    The file is private from the moment it is stored; only moderators and the
    uploader can reach it until a moderator approves it."""
    with transaction.atomic():
        resource = Resource(
            title=title or title_from_filename(validated.safe_name),
            description=description or "",
            course=course, category=category, uploader=user,
            original_filename=validated.safe_name, extension=validated.extension,
            mime_type=validated.mime_type, file_size=validated.size, sha256=validated.sha256,
        )
        resource.file.save(uploaded.name, uploaded, save=False)  # upload_path() ignores the user's name
        resource.save()
        for name in parse_tags(tags):
            tag, _ = ResourceTag.objects.get_or_create(name=name)
            resource.tags.add(tag)
        audit.record(user, "resource.upload", resource, f"{validated.safe_name} ({validated.size} bytes)")

    result = scan_resource(resource)
    if result.status == Resource.ScanStatus.INFECTED:
        quarantine_infected(resource, result.detail)
    return resource


def quarantine_infected(resource, detail):
    """Reject automatically and delete the stored file."""
    resource.file.delete(save=False)
    resource.file = ""
    resource.status = Resource.Status.REJECTED
    resource.rejection_reason = "This file failed the automatic security scan."
    resource.reviewed_at = timezone.now()
    resource.save(update_fields=["file", "status", "rejection_reason", "reviewed_at"])
    audit.record(None, "resource.quarantined", resource, detail)
