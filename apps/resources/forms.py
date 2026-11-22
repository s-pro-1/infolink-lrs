from django import forms
from django.conf import settings
from django.db.models import Case, IntegerField, Value, When

from apps.academics.models import Course

from .models import Resource, ResourceCategory
from .services import over_upload_limit
from .validators import ALLOWED_LABEL, validate_upload


class ResourceUploadForm(forms.ModelForm):
    file = forms.FileField(
        label="File",
        help_text="",  # filled in __init__ (depends on settings)
        widget=forms.ClearableFileInput(attrs={"accept": ".pdf,.doc,.docx,.ppt,.pptx,.txt"}),
    )
    tags = forms.CharField(required=False, max_length=200, label="Tags",
                           help_text="Optional. Separate with commas, for example: midterm, sql, 2024")
    declaration = forms.BooleanField(
        label="I have the right to share this material and it is relevant to the course.",
        error_messages={"required": "Please confirm you have the right to share this file."})

    class Meta:
        model = Resource
        fields = ("title", "course", "category", "description")
        labels = {"title": "Title"}
        help_texts = {"title": "Leave empty to use the file name."}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.validated = None
        self.fields["file"].help_text = f"{ALLOWED_LABEL}. Up to {settings.MAX_UPLOAD_MB} MB."
        self.fields["title"].required = False
        self.fields["description"].required = False
        self.fields["category"].queryset = ResourceCategory.objects.filter(is_active=True)

        courses = Course.objects.filter(is_active=True).select_related("department")
        profile = getattr(user, "student_profile", None) or getattr(user, "lecturer_profile", None)
        dept_id = getattr(profile, "department_id", None)
        if dept_id:  # the user's own department first
            courses = courses.annotate(
                _mine=Case(When(department_id=dept_id, then=Value(0)), default=Value(1), output_field=IntegerField())
            ).order_by("_mine", "code")
        self.fields["course"].queryset = courses
        for name, f in self.fields.items():
            w = f.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs["class"] = "form-check-input"
            elif isinstance(w, forms.Select):
                w.attrs["class"] = "form-select"
            else:
                w.attrs.setdefault("class", "form-control")

    def clean_file(self):
        self.validated = validate_upload(self.cleaned_data["file"])
        return self.cleaned_data["file"]

    def clean(self):
        data = super().clean()
        if self.user is not None and over_upload_limit(self.user):
            raise forms.ValidationError(
                f"You have reached the limit of {settings.UPLOADS_PER_HOUR} uploads per hour. Please try again later.")
        return data
