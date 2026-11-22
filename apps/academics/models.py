"""Configurable academic structure. Nothing here is hardcoded university data;
administrators create campuses, departments, programs and courses."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Campus(models.Model):
    name = models.CharField(max_length=120, unique=True)
    city = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "campuses"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(models.Model):
    campus = models.ForeignKey(Campus, on_delete=models.CASCADE, related_name="departments")
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["campus", "name"], name="uniq_department_per_campus"),
        ]

    def __str__(self):
        return f"{self.name} ({self.campus.name})"


class AcademicProgram(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="programs")
    name = models.CharField(max_length=150)
    duration_years = models.PositiveSmallIntegerField(default=4)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["department", "name"], name="uniq_program_per_department"),
        ]

    def __str__(self):
        return self.name


class AcademicYear(models.Model):
    label = models.CharField(max_length=20, unique=True, help_text="e.g. 2018 E.C. or 2025/26")
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["-label"]

    def __str__(self):
        return self.label


class Semester(models.Model):
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.CASCADE, related_name="semesters")
    name = models.CharField(max_length=40, help_text="e.g. Semester I")
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ["academic_year", "name"]
        constraints = [
            models.UniqueConstraint(fields=["academic_year", "name"], name="uniq_semester_per_year"),
        ]

    def __str__(self):
        return f"{self.academic_year} - {self.name}"


class Course(models.Model):
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="courses")
    programs = models.ManyToManyField(AcademicProgram, blank=True, related_name="courses")
    code = models.CharField(max_length=20)
    title = models.CharField(max_length=200)
    # Study level the course is normally taken in (1 = first year/semester block).
    level = models.PositiveSmallIntegerField(default=1, help_text="Year/level the course is usually taken")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["department", "code"], name="uniq_course_code_per_department"),
        ]
        indexes = [models.Index(fields=["title"])]

    def __str__(self):
        return f"{self.code} - {self.title}"


class StudentCourseEnrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["student", "course"], name="uniq_student_course"),
        ]

    def clean(self):
        if self.student_id and self.student.role != "student":
            raise ValidationError("Only students can enroll in courses.")

    def __str__(self):
        return f"{self.student} -> {self.course}"
