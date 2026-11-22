from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render

from apps.resources.models import Resource


def home(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    return render(request, "core/home.html")


def about(request):
    return render(request, "core/about.html")


@login_required
def dashboard(request):
    """Role-aware landing page. Resource widgets are added in later increments."""
    user = request.user
    ctx = {"enrolled": []}
    if user.is_student:
        enrolled = [e.course for e in user.enrollments.select_related("course").order_by("course__code")]
        profile = getattr(user, "student_profile", None)
        steps = [
            {"label": "Choose your department and program",
             "done": bool(profile and profile.department_id and profile.program_id)},
            {"label": "Pick the courses you take", "done": bool(enrolled)},
            {"label": "Add topics you are interested in", "done": bool(profile and profile.interests.strip())},
        ]
        done = sum(s["done"] for s in steps)
        ctx.update(
            enrolled=enrolled, steps=steps, steps_done=done,
            steps_percent=round(100 * done / len(steps)),
            course_materials=(Resource.objects.approved()
                              .filter(course__in=enrolled)
                              .select_related("course", "category").order_by("-created_at")[:6]),
        )
    if user.is_moderator:
        ctx["pending_count"] = Resource.objects.filter(status=Resource.Status.PENDING).count()
    return render(request, "core/dashboard.html", ctx)


def health(request):
    """Liveness/readiness probe for the hosting platform."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
        return JsonResponse({"status": "ok"})
    except Exception:  # noqa: BLE001 - any DB failure means not ready
        return JsonResponse({"status": "database unavailable"}, status=503)
