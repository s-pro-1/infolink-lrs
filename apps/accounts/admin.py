from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import LecturerProfile, StudentProfile, User


@admin.action(description="Verify selected users")
def verify_users(modeladmin, request, queryset):
    queryset.update(is_verified=True)


@admin.action(description="Deactivate selected users")
def deactivate_users(modeladmin, request, queryset):
    queryset.update(is_active=False)


@admin.register(User)
class PlatformUserAdmin(UserAdmin):
    list_display = ("username", "email", "role", "is_verified", "is_active")
    list_filter = ("role", "is_verified", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    actions = [verify_users, deactivate_users]
    fieldsets = UserAdmin.fieldsets + (("Platform", {"fields": ("role", "is_verified")}),)


admin.site.register(StudentProfile)
admin.site.register(LecturerProfile)
