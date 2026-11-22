from django.contrib import admin

from .models import Resource, ResourceCategory, ResourceDownload, ResourceTag


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "uploader", "status", "scan_status", "created_at")
    list_filter = ("status", "scan_status", "category")
    search_fields = ("title", "uploader__username", "course__code")
    # Approval goes through the moderation screens so it is checked and audited.
    readonly_fields = ("status", "scan_status", "scan_detail", "reviewed_by", "reviewed_at", "sha256",
                       "file_size", "mime_type", "extension", "original_filename", "download_count", "file")


admin.site.register(ResourceCategory)
admin.site.register(ResourceTag)
admin.site.register(ResourceDownload)
