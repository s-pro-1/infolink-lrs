import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.text import slugify

from .storage import get_private_storage


class ResourceCategory(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "resource categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ResourceTag(models.Model):
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ResourceQuerySet(models.QuerySet):
    def approved(self):
        """The only resources ordinary users may see in lists, search or downloads."""
        return self.filter(status=Resource.Status.APPROVED)

    def search(self, text):
        if not text:
            return self
        return self.filter(
            Q(title__icontains=text) | Q(description__icontains=text)
            | Q(tags__name__icontains=text) | Q(course__code__icontains=text)
            | Q(course__title__icontains=text)
        ).distinct()


def upload_path(instance, filename):
    """Storage key: random id + validated extension. The user's filename never
    becomes part of the path, so it cannot cause path tricks or collisions."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"resources/{instance.id.hex[:2]}/{instance.id.hex}.{ext}"


class Resource(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        HIDDEN = "hidden", "Hidden"

    class ScanStatus(models.TextChoices):
        PENDING = "pending", "Not scanned yet"
        CLEAN = "clean", "Clean"
        INFECTED = "infected", "Threat found"
        UNAVAILABLE = "unavailable", "Scanner unavailable"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, max_length=2000)
    course = models.ForeignKey("academics.Course", on_delete=models.PROTECT, related_name="resources")
    category = models.ForeignKey(ResourceCategory, on_delete=models.PROTECT, related_name="resources")
    tags = models.ManyToManyField(ResourceTag, blank=True, related_name="resources")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="resources")

    file = models.FileField(upload_to=upload_path, storage=get_private_storage, max_length=255, blank=True)
    original_filename = models.CharField(max_length=200)
    extension = models.CharField(max_length=5)
    mime_type = models.CharField(max_length=100)
    file_size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    scan_status = models.CharField(max_length=12, choices=ScanStatus.choices, default=ScanStatus.PENDING)
    scan_detail = models.CharField(max_length=200, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name="reviewed_resources")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = ResourceQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["course", "status"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_approved(self):
        return self.status == self.Status.APPROVED

    @property
    def type_label(self):
        return self.extension.upper()

    @property
    def size_label(self):
        size = float(self.file_size)
        for unit in ("B", "KB", "MB"):
            if size < 1024 or unit == "MB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024

    def can_be_seen_by(self, user):
        """Approved: any signed-in user. Otherwise only the uploader and moderators."""
        if not user.is_authenticated or not user.is_active:
            return False
        return self.is_approved or user.is_moderator or self.uploader_id == user.id


class ResourceDownload(models.Model):
    """One row per authorized download of an approved resource."""
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name="downloads")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="downloads")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]
