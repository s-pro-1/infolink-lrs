from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.academics.models import AcademicProgram, Campus, Course, Department

from .models import LecturerProfile, StudentProfile, User


class BootstrapMixin:
    def _style(self):
        for f in self.fields.values():
            css = "form-select" if isinstance(f.widget, forms.Select) else "form-control"
            if isinstance(f.widget, forms.CheckboxInput):
                css = "form-check-input"
            f.widget.attrs.setdefault("class", css)


class RegistrationForm(BootstrapMixin, UserCreationForm):
    """Public registration. The role is NOT a form field: it is fixed by the view,
    so nobody can self-assign lecturer, moderator or admin privileges."""
    first_name = forms.CharField(max_length=60)
    last_name = forms.CharField(max_length=60)
    email = forms.EmailField()
    campus = forms.ModelChoiceField(Campus.objects.filter(is_active=True), required=False)
    department = forms.ModelChoiceField(Department.objects.all(), required=False)
    account_type = forms.ChoiceField(
        choices=[("student", "Student"), ("lecturer", "Lecturer (needs admin verification)")],
        initial="student",
    )
    staff_note = forms.CharField(
        required=False, max_length=200, label="Lecturer verification details",
        help_text="Lecturers only: department or staff details so an administrator can verify you.")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        # Hard-coded allow-list: public registration can only yield these two roles.
        user.role = User.Role.LECTURER if self.cleaned_data["account_type"] == "lecturer" else User.Role.STUDENT
        user.is_verified = False
        if commit:
            user.save()
            if user.is_lecturer:
                LecturerProfile.objects.create(
                    user=user, campus=self.cleaned_data.get("campus"),
                    department=self.cleaned_data.get("department"),
                    staff_note=self.cleaned_data.get("staff_note", ""))
            else:
                StudentProfile.objects.create(
                    user=user, campus=self.cleaned_data.get("campus"),
                    department=self.cleaned_data.get("department"))
        return user


class StudentProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ("campus", "department", "program", "current_level", "interests")
        help_texts = {"interests": "Comma-separated topics, e.g. databases, networking, python"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        self.fields["program"].queryset = AcademicProgram.objects.select_related("department")

    def clean(self):
        data = super().clean()
        dept, program = data.get("department"), data.get("program")
        if dept and program and program.department_id != dept.id:
            self.add_error("program", "This program does not belong to the selected department.")
        return data


class CourseSelectionForm(forms.Form):
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.none(), required=False, widget=forms.CheckboxSelectMultiple)

    def __init__(self, *args, department=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Course.objects.filter(is_active=True).select_related("department")
        if department:
            qs = qs.filter(department=department)
        self.fields["courses"].queryset = qs


class UserNamesForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email
