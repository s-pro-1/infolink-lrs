from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import F
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.academics.models import Course

from .forms import ResourceUploadForm
from .models import Resource, ResourceCategory, ResourceDownload
from .services import create_resource


@login_required
def browse(request):
    """Approved resources only. Pending, rejected and hidden items never appear here."""
    qs = Resource.objects.approved().select_related("course", "category").prefetch_related("tags")
    q = request.GET.get("q", "").strip()
    course_id = request.GET.get("course", "")
    category_id = request.GET.get("category", "")
    qs = qs.search(q)
    if course_id.isdigit():
        qs = qs.filter(course_id=course_id)
    if category_id.isdigit():
        qs = qs.filter(category_id=category_id)
    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "resources/browse.html", {
        "page": page, "q": q, "course_id": course_id, "category_id": category_id,
        "courses": Course.objects.filter(is_active=True).order_by("code"),
        "categories": ResourceCategory.objects.filter(is_active=True),
        "querystring": params.urlencode(),
    })


@login_required
@require_http_methods(["GET", "POST"])
def upload(request):
    if not request.user.can_upload:
        if request.user.is_moderator:
            messages.info(request, "Moderators review material. Uploading is for students and lecturers.")
        else:
            messages.warning(request, "Uploading opens once an administrator has verified your account.")
        return redirect("core:dashboard")
    form = ResourceUploadForm(request.POST or None, request.FILES or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        resource = create_resource(
            user=request.user, uploaded=form.cleaned_data["file"], validated=form.validated,
            title=form.cleaned_data["title"].strip(), description=form.cleaned_data["description"],
            course=form.cleaned_data["course"], category=form.cleaned_data["category"],
            tags=form.cleaned_data["tags"])
        if resource.status == Resource.Status.REJECTED:
            messages.error(request, "This file failed the automatic security check and was not accepted.")
        else:
            messages.success(request, "Uploaded. A moderator will review it before it is shared.")
        return redirect("resources:mine")
    return render(request, "resources/upload.html", {"form": form})


@login_required
def my_uploads(request):
    items = Resource.objects.filter(uploader=request.user).select_related("course", "category")
    return render(request, "resources/mine.html", {"items": items})


def _visible_or_404(request, pk):
    resource = get_object_or_404(Resource.objects.select_related("course", "category", "uploader"), pk=pk)
    if not resource.can_be_seen_by(request.user):
        raise Http404  # 404, not 403: do not reveal that a private item exists
    return resource


@login_required
def detail(request, pk):
    resource = _visible_or_404(request, pk)
    return render(request, "resources/detail.html", {
        "resource": resource,
        "can_download": bool(resource.file),
        "tags": resource.tags.all(),
    })


@login_required
def download(request, pk):
    """Authorization happens here, in Django, for every download."""
    resource = _visible_or_404(request, pk)
    if not resource.file:
        raise Http404
    if resource.is_approved and resource.uploader_id != request.user.id:
        ResourceDownload.objects.create(resource=resource, user=request.user)
        Resource.objects.filter(pk=resource.pk).update(download_count=F("download_count") + 1)
    response = FileResponse(resource.file.open("rb"), as_attachment=True, filename=resource.original_filename)
    response["Content-Type"] = resource.mime_type
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response
