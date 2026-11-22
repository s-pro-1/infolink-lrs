from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from apps.academics.models import AcademicProgram, Campus, Course, Department
from apps.academics.services import set_student_courses

from .models import StudentProfile, User

PASSWORD = "Str0ng-pass-phrase!"


def reg_data(**over):
    data = {
        "username": "selam", "first_name": "Selam", "last_name": "T",
        "email": "selam@example.com", "password1": PASSWORD, "password2": PASSWORD,
        "account_type": "student",
    }
    data.update(over)
    return data


class AcademicFixtureMixin:
    @classmethod
    def setUpTestData(cls):
        cls.campus = Campus.objects.create(name="Test Campus")
        cls.dept = Department.objects.create(campus=cls.campus, name="Test Dept")
        cls.other_dept = Department.objects.create(campus=cls.campus, name="Other Dept")
        cls.program = AcademicProgram.objects.create(department=cls.dept, name="Test Program")
        cls.c1 = Course.objects.create(department=cls.dept, code="T1", title="Course One")
        cls.c2 = Course.objects.create(department=cls.dept, code="T2", title="Course Two")
        cls.c_other = Course.objects.create(department=cls.other_dept, code="O1", title="Other Course")


class RegistrationTests(AcademicFixtureMixin, TestCase):
    def test_student_registration_creates_unverified_student_with_profile(self):
        r = self.client.post(reverse("accounts:register"), reg_data())
        self.assertRedirects(r, reverse("accounts:profile"))
        u = User.objects.get(username="selam")
        self.assertEqual(u.role, User.Role.STUDENT)
        self.assertFalse(u.is_verified)
        self.assertTrue(StudentProfile.objects.filter(user=u).exists())
        self.assertTrue(u.check_password(PASSWORD))  # hashed, usable

    def test_lecturer_registration_is_unverified_and_cannot_upload(self):
        self.client.post(reverse("accounts:register"), reg_data(account_type="lecturer", staff_note="CS dept"))
        u = User.objects.get(username="selam")
        self.assertEqual(u.role, User.Role.LECTURER)
        self.assertFalse(u.is_verified)
        self.assertFalse(u.can_upload)
        self.assertEqual(u.lecturer_profile.staff_note, "CS dept")

    def test_cannot_self_assign_privileged_role_or_flags(self):
        for role in ("admin", "moderator"):
            self.client.post(reverse("accounts:register"), reg_data(
                username=f"x{role}", email=f"{role}@example.com",
                role=role, account_type=role, is_staff="on", is_superuser="on", is_verified="on"))
        # Invalid account_type is rejected outright; extra fields are ignored.
        self.assertFalse(User.objects.filter(role__in=["admin", "moderator"]).exists())
        self.assertFalse(User.objects.filter(is_staff=True).exists())
        self.client.post(reverse("accounts:register"), reg_data(is_verified="on", is_staff="on"))
        u = User.objects.get(username="selam")
        self.assertFalse(u.is_verified)
        self.assertFalse(u.is_staff)

    def test_duplicate_email_rejected_case_insensitively(self):
        User.objects.create_user("a", "Selam@Example.com", PASSWORD)
        r = self.client.post(reverse("accounts:register"), reg_data())
        self.assertContains(r, "already exists")
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_rejected(self):
        r = self.client.post(reverse("accounts:register"), reg_data(password1="12345678", password2="12345678"))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_superuser_role_forced_to_admin(self):
        su = User.objects.create_superuser("root", "root@example.com", PASSWORD)
        self.assertEqual(su.role, User.Role.ADMIN)


class AuthTests(AcademicFixtureMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user("bob", "bob@example.com", PASSWORD)

    def test_login_and_logout(self):
        r = self.client.post(reverse("accounts:login"), {"username": "bob", "password": PASSWORD})
        self.assertRedirects(r, reverse("core:dashboard"), fetch_redirect_response=False)
        self.client.post(reverse("accounts:logout"))
        self.assertEqual(self.client.get(reverse("core:dashboard")).status_code, 302)

    def test_dashboard_requires_login(self):
        r = self.client.get(reverse("core:dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r["Location"])

    def test_inactive_user_cannot_log_in(self):
        self.user.is_active = False
        self.user.save()
        r = self.client.post(reverse("accounts:login"), {"username": "bob", "password": PASSWORD})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_throttled_after_repeated_failures(self):
        for _ in range(5):
            self.client.post(reverse("accounts:login"), {"username": "bob", "password": "wrong"})
        r = self.client.post(reverse("accounts:login"), {"username": "bob", "password": PASSWORD})
        self.assertEqual(r.status_code, 429)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("accounts:logout")).status_code, 405)

    def test_password_change(self):
        self.client.force_login(self.user)
        new = "An0ther-Str0ng-pass!"
        r = self.client.post(reverse("accounts:password_change"), {
            "old_password": PASSWORD, "new_password1": new, "new_password2": new})
        self.assertEqual(r.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new))

    def test_password_reset_does_not_reveal_whether_email_exists(self):
        r1 = self.client.post(reverse("accounts:password_reset"), {"email": "bob@example.com"})
        r2 = self.client.post(reverse("accounts:password_reset"), {"email": "nobody@example.com"})
        self.assertEqual(r1["Location"], r2["Location"])


class ProfileTests(AcademicFixtureMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user("stu", "stu@example.com", PASSWORD)
        StudentProfile.objects.create(user=self.user)
        self.client.force_login(self.user)

    def _post(self, **over):
        data = {
            "u-first_name": "Stu", "u-last_name": "Dent", "u-email": "stu@example.com",
            "p-campus": self.campus.id, "p-department": self.dept.id, "p-program": self.program.id,
            "p-current_level": 2, "p-interests": "Databases, Python ",
            "c-courses": [self.c1.id],
        }
        data.update(over)
        return self.client.post(reverse("accounts:profile"), data)

    def test_profile_and_course_enrollment_saved(self):
        r = self._post()
        self.assertRedirects(r, reverse("accounts:profile"))
        # Query fresh: self.user caches the profile object created in setUp.
        sp = StudentProfile.objects.get(user=self.user)
        self.assertEqual(sp.department, self.dept)
        self.assertEqual(sp.interest_list(), ["databases", "python"])
        self.assertEqual(list(self.user.enrollments.values_list("course_id", flat=True)), [self.c1.id])

    def test_enrollment_can_be_changed(self):
        self._post()
        self._post(**{"c-courses": [self.c2.id]})
        self.assertEqual(list(self.user.enrollments.values_list("course_id", flat=True)), [self.c2.id])

    def test_cannot_enroll_in_course_of_another_department(self):
        self._post(**{"c-courses": [self.c_other.id]})
        self.assertFalse(self.user.enrollments.exists())

    def test_program_must_match_department(self):
        r = self._post(**{"p-department": self.other_dept.id})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "does not belong")

    def test_email_uniqueness_on_profile_edit(self):
        User.objects.create_user("other", "taken@example.com", PASSWORD)
        r = self._post(**{"u-email": "taken@example.com"})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "stu@example.com")

    def test_set_student_courses_is_idempotent(self):
        set_student_courses(self.user, [self.c1, self.c2])
        set_student_courses(self.user, [self.c1, self.c2])
        self.assertEqual(self.user.enrollments.count(), 2)

    def test_profile_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("accounts:profile")).status_code, 302)


class CoreViewTests(TestCase):
    def test_public_pages_and_health(self):
        for name in ("core:home", "core:about", "accounts:login", "accounts:register"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)
        r = self.client.get(reverse("core:health"))
        self.assertEqual(r.json(), {"status": "ok"})

    def test_lecturer_sees_verification_notice(self):
        u = User.objects.create_user("lec", "lec@example.com", PASSWORD, role=User.Role.LECTURER)
        self.client.force_login(u)
        self.assertContains(self.client.get(reverse("core:dashboard")), "waiting for administrator verification")
