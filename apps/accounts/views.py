from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db import transaction
from django.shortcuts import redirect, render

from apps.academics.services import set_student_courses

from .forms import CourseSelectionForm, RegistrationForm, StudentProfileForm, UserNamesForm
from .models import StudentProfile
from .throttle import LoginThrottleMixin


class ThrottledLoginView(LoginThrottleMixin, LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        if user.is_lecturer:
            messages.info(request, "Account created. An administrator must verify you before you can upload.")
        else:
            messages.success(request, "Welcome! Complete your academic profile to get recommendations.")
        return redirect("accounts:profile")
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    user = request.user
    names_form = UserNamesForm(request.POST or None, instance=user, prefix="u")
    profile_form = course_form = None
    if user.is_student:
        sp, _ = StudentProfile.objects.get_or_create(user=user)
        profile_form = StudentProfileForm(request.POST or None, instance=sp, prefix="p")
        course_form = CourseSelectionForm(
            request.POST or None, department=sp.department, prefix="c",
            initial={"courses": user.enrollments.values_list("course_id", flat=True)})
    if request.method == "POST":
        forms_ok = names_form.is_valid() and (profile_form is None or profile_form.is_valid())
        if forms_ok:
            with transaction.atomic():
                names_form.save()
                if profile_form:
                    sp = profile_form.save()
                    # Re-bind the course list to the (possibly changed) department.
                    course_form = CourseSelectionForm(request.POST, department=sp.department, prefix="c")
                    if course_form.is_valid():
                        set_student_courses(user, course_form.cleaned_data["courses"])
            messages.success(request, "Profile saved.")
            return redirect("accounts:profile")
    return render(request, "accounts/profile.html", {
        "names_form": names_form, "profile_form": profile_form, "course_form": course_form})
