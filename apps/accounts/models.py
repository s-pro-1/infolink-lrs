from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        LECTURER = "lecturer", "Lecturer"
        MODERATOR = "moderator", "Moderator"
        ADMIN = "admin", "Administrator"

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.STUDENT)
    # Admin-managed verification; unverified users cannot upload (enforced in Increment 2).
    is_verified = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Superusers are always administrators; avoids a staff account with a student role.
        if self.is_superuser:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_lecturer(self):
        return self.role == self.Role.LECTURER

    @property
    def is_moderator(self):
        return self.role in (self.Role.MODERATOR, self.Role.ADMIN)

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def can_upload(self):
        return self.is_active and self.is_verified and self.role in (
            self.Role.STUDENT, self.Role.LECTURER)

    def __str__(self):
        return self.get_full_name() or self.username


class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="student_profile")
    campus = models.ForeignKey("academics.Campus", null=True, blank=True, on_delete=models.SET_NULL)
    department = models.ForeignKey("academics.Department", null=True, blank=True, on_delete=models.SET_NULL)
    program = models.ForeignKey("academics.AcademicProgram", null=True, blank=True, on_delete=models.SET_NULL)
    current_level = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Current year/level")
    # Comma-separated keywords used by the recommendation engine (Increment 4).
    interests = models.CharField(max_length=300, blank=True)

    def interest_list(self):
        return [i.strip().lower() for i in self.interests.split(",") if i.strip()]

    def __str__(self):
        return f"Profile of {self.user}"


class LecturerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="lecturer_profile")
    campus = models.ForeignKey("academics.Campus", null=True, blank=True, on_delete=models.SET_NULL)
    department = models.ForeignKey("academics.Department", null=True, blank=True, on_delete=models.SET_NULL)
    staff_note = models.CharField(
        max_length=200, blank=True,
        help_text="Details the applicant gives so an admin can verify them")

    def __str__(self):
        return f"Lecturer profile of {self.user}"
