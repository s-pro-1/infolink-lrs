from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core import audit
from apps.resources.models import Resource
from apps.resources.scanning import scan_resource
from apps.resources.services import quarantine_infected

from . import services


def moderator_required(view):
    """Signed-in, active moderators and administrators only."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_active and request.user.is_moderator):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapper


@moderator_required
def queue(request):
    show = request.GET.get("show", "pending")
    statuses = {
        "pending": [Resource.Status.PENDING],
        "approved": [Resource.Status.APPROVED, Resource.Status.HIDDEN],
        "rejected": [Resource.Status.REJECTED],
    }.get(show, [Resource.Status.PENDING])
    items = (Resource.objects.filter(status__in=statuses)
             .select_related("course", "category", "uploader").order_by("created_at" if show == "pending" else "-created_at"))
    counts = {
        "pending": Resource.objects.filter(status=Resource.Status.PENDING).count(),
    }
    return render(request, "moderation/queue.html", {"items": items[:100], "show": show, "counts": counts})


@moderator_required
def review(request, pk):
    resource = get_object_or_404(Resource.objects.select_related("course", "category", "uploader", "reviewed_by"), pk=pk)
    return render(request, "moderation/review.html", {
        "resource": resource, "can_approve": services.can_approve(resource),
        "tags": resource.tags.all(),
        "dev_unscanned": resource.scan_status != Resource.ScanStatus.CLEAN,
    })


def _act(request, pk, action):
    resource = get_object_or_404(Resource, pk=pk)
    try:
        action(resource, request.user)
    except services.ModerationError as exc:
        messages.error(request, str(exc))
        return None
    return resource


@moderator_required
@require_POST
def approve(request, pk):
    if _act(request, pk, services.approve):
        messages.success(request, "Approved. It is now visible to students.")
        return redirect("moderation:queue")
    return redirect("moderation:review", pk=pk)


@moderator_required
@require_POST
def reject(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    try:
        services.reject(resource, request.user, request.POST.get("reason", ""))
    except services.ModerationError as exc:
        messages.error(request, str(exc))
        return redirect("moderation:review", pk=pk)
    messages.success(request, "Rejected. The uploader can see your reason.")
    return redirect("moderation:queue")


@moderator_required
@require_POST
def hide(request, pk):
    if _act(request, pk, services.hide):
        messages.success(request, "Hidden. Students can no longer see it.")
    return redirect("moderation:review", pk=pk)


@moderator_required
@require_POST
def restore(request, pk):
    if _act(request, pk, services.restore):
        messages.success(request, "Restored to approved.")
    return redirect("moderation:review", pk=pk)


@moderator_required
@require_POST
def rescan(request, pk):
    resource = get_object_or_404(Resource, pk=pk)
    if not resource.file:
        messages.error(request, "There is no stored file to scan.")
        return redirect("moderation:review", pk=pk)
    result = scan_resource(resource)
    audit.record(request.user, "resource.rescan", resource, result.status)
    if result.status == Resource.ScanStatus.INFECTED:
        quarantine_infected(resource, result.detail)
        messages.error(request, "A threat was found. The file was rejected and deleted.")
        return redirect("moderation:queue")
    messages.info(request, f"Scan result: {resource.get_scan_status_display().lower()}.")
    return redirect("moderation:review", pk=pk)
