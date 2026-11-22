from django.contrib import admin

from .models import (AcademicProgram, AcademicYear, Campus, Course, Department,
                     Semester, StudentCourseEnrollment)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "department", "level", "is_active")
    list_filter = ("department", "level", "is_active")
    search_fields = ("code", "title")
    filter_horizontal = ("programs",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "campus", "code")
    list_filter = ("campus",)


admin.site.register(Campus)
admin.site.register(AcademicProgram)
admin.site.register(AcademicYear)
admin.site.register(Semester)
admin.site.register(StudentCourseEnrollment)
