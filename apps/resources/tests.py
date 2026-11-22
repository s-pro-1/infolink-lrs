import io
import shutil
import tempfile
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.academics.models import Campus, Course, Department
from apps.accounts.models import StudentProfile, User
from apps.core.models import AuditLog
from apps.moderation import services as mod
from apps.resources.models import Resource, ResourceCategory
from apps.resources.scanning import ClamAVScanner, ScanResult
from apps.resources.services import create_resource, parse_tags
from apps.resources.validators import validate_upload
from django.core.exceptions import ValidationError

PW = "Str0ng-pass-phrase!"


class FakeCleanScanner:
    def scan(self, fileobj):
        return ScanResult(Resource.ScanStatus.CLEAN, "ok")


class FakeInfectedScanner:
    def scan(self, fileobj):
        return ScanResult(Resource.ScanStatus.INFECTED, "Test.Signature")


def pdf(size=200):
    return b"%PDF-1.4\n" + b"x" * size


def office(kind="word", extra=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr(f"{kind}/document.xml", "<doc/>")
        for name in extra or []:
            z.writestr(name, "x")
    return buf.getvalue()


def upfile(name, data, ctype="application/octet-stream"):
    return SimpleUploadedFile(name, data, content_type=ctype)


class StorageMixin:
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.mkdtemp()
        self._ov = override_settings(PRIVATE_MEDIA_ROOT=self.tmp, RESOURCE_SCANNER="")
        self._ov.enable()
        self.addCleanup(self._ov.disable)
        self.addCleanup(shutil.rmtree, self.tmp, True)


class Fixture(StorageMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        campus = Campus.objects.create(name="C")
        cls.dept = Department.objects.create(campus=campus, name="D")
        cls.course = Course.objects.create(department=cls.dept, code="X1", title="Databases")
        cls.course2 = Course.objects.create(department=cls.dept, code="X2", title="Networks")
        cls.cat = ResourceCategory.objects.get(name="Lecture Notes")
        mk = lambda n, **kw: User.objects.create_user(n, f"{n}@example.com", PW, **kw)
        cls.alice = mk("alice", is_verified=True)
        cls.bob = mk("bob", is_verified=True)
        cls.unverified = mk("newbie")
        cls.lecturer = mk("lect", role=User.Role.LECTURER, is_verified=True)
        cls.mod = mk("mod", role=User.Role.MODERATOR, is_verified=True)
        for u in (cls.alice, cls.bob, cls.unverified):
            StudentProfile.objects.create(user=u, department=cls.dept)

    def make(self, user=None, status=Resource.Status.PENDING, name="notes.pdf", data=None, **kw):
        up = upfile(name, data or pdf())
        r = create_resource(
            user=user or self.alice, uploaded=up, validated=validate_upload(up),
            title=kw.pop("title", "Sample notes"), description="", course=kw.pop("course", self.course),
            category=self.cat, tags=kw.pop("tags", ""))
        if status != Resource.Status.PENDING:
            r.status = status
            r.save()
        return r


class ValidatorTests(StorageMixin, TestCase):
    def check_rejected(self, name, data):
        with self.assertRaises(ValidationError):
            validate_upload(upfile(name, data))

    def test_accepts_valid_types(self):
        for name, data in [("a.pdf", pdf()), ("a.txt", b"plain notes\nline two"),
                           ("a.docx", office("word")), ("a.pptx", office("ppt")),
                           ("a.doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 50),
                           ("a.ppt", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 50)]:
            v = validate_upload(upfile(name, data))
            self.assertEqual(v.extension, name.split(".")[1])
            self.assertEqual(len(v.sha256), 64)

    def test_rejects_disallowed_extensions(self):
        for name in ["run.exe", "page.html", "x.js", "a.zip", "noext", "evil.pdf.exe", "a.svg"]:
            self.check_rejected(name, pdf())

    def test_rejects_content_that_does_not_match_extension(self):
        self.check_rejected("fake.pdf", b"MZ\x90\x00 this is an exe")
        self.check_rejected("fake.docx", b"%PDF-1.4 not a zip")
        self.check_rejected("fake.doc", b"%PDF-1.4")
        self.check_rejected("fake.pdf", b"")

    def test_word_file_with_pptx_extension_rejected(self):
        self.check_rejected("a.pptx", office("word"))
        self.check_rejected("a.docx", office("ppt"))

    def test_macros_and_programs_inside_office_files_rejected(self):
        self.check_rejected("a.docx", office("word", ["word/vbaProject.bin"]))
        self.check_rejected("a.pptx", office("ppt", ["ppt/run.exe"]))

    def test_path_traversal_inside_zip_rejected(self):
        self.check_rejected("a.docx", office("word", ["../evil.txt"]))

    def test_damaged_zip_rejected(self):
        self.check_rejected("a.docx", b"PK\x03\x04" + b"garbage" * 20)

    def test_txt_that_is_html_or_binary_rejected(self):
        self.check_rejected("a.txt", b"<!DOCTYPE html><html><script>alert(1)</script>")
        self.check_rejected("a.txt", b"<script>alert(1)</script>")
        self.check_rejected("a.txt", b"abc\x00\x01\x02binary")

    @override_settings(MAX_UPLOAD_MB=1)
    def test_size_limit(self):
        self.check_rejected("big.pdf", pdf(1024 * 1024 + 10))
        validate_upload(upfile("ok.pdf", pdf(1000)))

    def test_filename_is_sanitized(self):
        v = validate_upload(upfile("../../etc/pass wd<script>.pdf", pdf()))
        self.assertNotIn("/", v.safe_name)
        self.assertNotIn("<", v.safe_name)
        self.assertTrue(v.safe_name.endswith(".pdf"))


class ScannerTests(Fixture):
    @override_settings(RESOURCE_SCANNER="apps.resources.tests.FakeCleanScanner")
    def test_clean_scan_recorded(self):
        self.assertEqual(self.make().scan_status, Resource.ScanStatus.CLEAN)

    def test_no_scanner_is_never_marked_clean(self):
        self.assertEqual(self.make().scan_status, Resource.ScanStatus.UNAVAILABLE)

    @override_settings(RESOURCE_SCANNER="apps.resources.tests.FakeInfectedScanner")
    def test_infected_file_is_rejected_and_deleted(self):
        r = self.make()
        self.assertEqual(r.status, Resource.Status.REJECTED)
        self.assertEqual(r.scan_status, Resource.ScanStatus.INFECTED)
        self.assertFalse(r.file)
        self.assertTrue(AuditLog.objects.filter(action="resource.quarantined").exists())

    def test_clamav_unreachable_fails_closed(self):
        result = ClamAVScanner(host="127.0.0.1", port=1, timeout=1).scan(io.BytesIO(b"data"))
        self.assertEqual(result.status, Resource.ScanStatus.UNAVAILABLE)

    def test_clamav_not_configured_fails_closed(self):
        result = ClamAVScanner(host="", unix_socket="").scan(io.BytesIO(b"data"))
        self.assertEqual(result.status, Resource.ScanStatus.UNAVAILABLE)


class UploadViewTests(Fixture):
    def post(self, user, name="notes.pdf", data=None, **over):
        self.client.force_login(user)
        body = {"file": upfile(name, data or pdf()), "title": "My notes", "course": self.course.id,
                "category": self.cat.id, "description": "d", "tags": "SQL, midterm, sql", "declaration": "on"}
        body.update(over)
        return self.client.post(reverse("resources:upload"), body)

    def test_verified_student_upload_is_pending_and_private(self):
        r = self.post(self.alice)
        self.assertRedirects(r, reverse("resources:mine"))
        res = Resource.objects.get()
        self.assertEqual(res.status, Resource.Status.PENDING)
        self.assertEqual(res.uploader, self.alice)
        self.assertEqual(sorted(res.tags.values_list("name", flat=True)), ["midterm", "sql"])
        self.assertTrue(AuditLog.objects.filter(action="resource.upload").exists())

    def test_storage_key_is_random_and_ignores_user_filename(self):
        self.post(self.alice, name="../../evil name.pdf")
        res = Resource.objects.get()
        self.assertRegex(res.file.name, r"^resources/[0-9a-f]{2}/[0-9a-f]{32}\.pdf$")
        self.assertNotIn("evil", res.file.name)

    def test_unverified_user_cannot_upload(self):
        r = self.post(self.unverified)
        self.assertRedirects(r, reverse("core:dashboard"), fetch_redirect_response=False)
        self.assertFalse(Resource.objects.exists())

    def test_moderator_cannot_upload(self):
        self.post(self.mod)
        self.assertFalse(Resource.objects.exists())

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse("resources:upload"))
        self.assertEqual(r.status_code, 302)

    def test_invalid_file_shows_friendly_error_and_stores_nothing(self):
        r = self.post(self.alice, name="virus.exe", data=b"MZ")
        self.assertContains(r, "Only PDF, DOC, DOCX, PPT, PPTX or TXT files can be uploaded.")
        self.assertFalse(Resource.objects.exists())

    def test_declaration_required(self):
        r = self.post(self.alice, declaration="")
        self.assertContains(r, "confirm you have the right to share")
        self.assertFalse(Resource.objects.exists())

    def test_empty_title_uses_file_name(self):
        self.post(self.alice, name="week_3-sql_notes.pdf", title="")
        self.assertEqual(Resource.objects.get().title, "week 3 sql notes")

    @override_settings(UPLOADS_PER_HOUR=2)
    def test_hourly_upload_limit(self):
        self.make()
        self.make()
        r = self.post(self.alice)
        self.assertContains(r, "limit of 2 uploads per hour")
        self.assertEqual(Resource.objects.count(), 2)

    def test_parse_tags(self):
        self.assertEqual(parse_tags("A, b ,,a\nc"), ["a", "b", "c"])
        self.assertEqual(len(parse_tags(",".join(str(i) for i in range(20)))), 8)


class AccessControlTests(Fixture):
    def test_pending_file_visible_only_to_uploader_and_moderator(self):
        r = self.make()
        for user, code in [(self.alice, 200), (self.mod, 200), (self.bob, 404)]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse("resources:detail", args=[r.pk])).status_code, code, user)
            self.assertEqual(self.client.get(reverse("resources:download", args=[r.pk])).status_code, code, user)

    def test_anonymous_cannot_download_even_approved(self):
        r = self.make(status=Resource.Status.APPROVED)
        resp = self.client.get(reverse("resources:download", args=[r.pk]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp["Location"])

    def test_approved_file_downloads_with_safe_headers_and_is_counted(self):
        r = self.make(status=Resource.Status.APPROVED)
        self.client.force_login(self.bob)
        resp = self.client.get(reverse("resources:download", args=[r.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(b"".join(resp.streaming_content)[:5], b"%PDF-")
        self.assertIn("attachment", resp["Content-Disposition"])
        self.assertEqual(resp["X-Content-Type-Options"], "nosniff")
        r.refresh_from_db()
        self.assertEqual(r.download_count, 1)
        self.assertEqual(r.downloads.count(), 1)

    def test_own_download_and_unapproved_not_counted(self):
        r = self.make(status=Resource.Status.APPROVED)
        self.client.force_login(self.alice)
        self.client.get(reverse("resources:download", args=[r.pk])).close()
        p = self.make(user=self.alice)
        self.client.get(reverse("resources:download", args=[p.pk])).close()
        self.assertEqual(Resource.objects.get(pk=r.pk).download_count, 0)
        self.assertEqual(Resource.objects.get(pk=p.pk).download_count, 0)

    def test_hidden_and_rejected_not_visible_to_others(self):
        self.client.force_login(self.bob)
        for st in (Resource.Status.HIDDEN, Resource.Status.REJECTED):
            r = self.make(status=st)
            self.assertEqual(self.client.get(reverse("resources:download", args=[r.pk])).status_code, 404)

    def test_private_storage_has_no_public_url(self):
        r = self.make()
        with self.assertRaises(ValueError):
            r.file.url


class BrowseTests(Fixture):
    def test_only_approved_appear_in_browse(self):
        self.make(title="Visible", status=Resource.Status.APPROVED)
        for st, t in [(Resource.Status.PENDING, "Pend"), (Resource.Status.REJECTED, "Rej"), (Resource.Status.HIDDEN, "Hid")]:
            self.make(title=t, status=st)
        self.client.force_login(self.bob)
        html = self.client.get(reverse("resources:browse")).content.decode()
        self.assertIn("Visible", html)
        for t in ("Pend", "Rej", "Hid"):
            self.assertNotIn(f">{t}<", html)

    def test_search_filter_and_empty_state(self):
        self.make(title="Normalization guide", status=Resource.Status.APPROVED, tags="sql")
        self.make(title="Routing basics", status=Resource.Status.APPROVED, course=self.course2)
        self.client.force_login(self.bob)
        get = lambda **q: self.client.get(reverse("resources:browse"), q).content.decode()
        self.assertIn("Normalization", get(q="normal"))
        self.assertNotIn("Routing", get(q="normal"))
        self.assertIn("Normalization", get(q="sql"))  # tag search
        self.assertIn("Routing", get(course=self.course2.id))
        self.assertNotIn("Normalization", get(course=self.course2.id))
        self.assertIn("No materials match your search", get(q="zzzz"))

    def test_pagination(self):
        for i in range(15):
            self.make(title=f"Item {i}", status=Resource.Status.APPROVED)
        self.client.force_login(self.bob)
        r = self.client.get(reverse("resources:browse"))
        self.assertEqual(len(r.context["page"].object_list), 12)
        self.assertEqual(len(self.client.get(reverse("resources:browse"), {"page": 2}).context["page"].object_list), 3)

    def test_my_uploads_shows_only_own_and_reason(self):
        mine = self.make(title="Mine only")
        self.make(user=self.bob, title="Bobs secret")
        mod.reject(mine, self.mod, "Wrong course material")
        self.client.force_login(self.alice)
        html = self.client.get(reverse("resources:mine")).content.decode()
        self.assertIn("Mine only", html)
        self.assertIn("Wrong course material", html)
        self.assertNotIn("Bobs secret", html)

    def test_dashboard_lists_materials_for_enrolled_courses_only(self):
        from apps.academics.services import set_student_courses
        set_student_courses(self.bob, [self.course])
        self.make(title="For my course", status=Resource.Status.APPROVED)
        self.make(title="Other course", status=Resource.Status.APPROVED, course=self.course2)
        self.client.force_login(self.bob)
        html = self.client.get(reverse("core:dashboard")).content.decode()
        self.assertIn("For my course", html)
        self.assertNotIn("Other course", html)


class ModerationTests(Fixture):
    def test_students_and_anonymous_cannot_use_moderation(self):
        r = self.make()
        urls = [reverse("moderation:queue"), reverse("moderation:review", args=[r.pk])]
        self.client.force_login(self.bob)
        for u in urls:
            self.assertEqual(self.client.get(u).status_code, 403)
        for name in ("approve", "reject", "hide", "restore", "rescan"):
            self.assertEqual(self.client.post(reverse(f"moderation:{name}", args=[r.pk])).status_code, 403, name)
        r.refresh_from_db()
        self.assertEqual(r.status, Resource.Status.PENDING)
        self.client.logout()
        self.assertEqual(self.client.get(urls[0]).status_code, 302)

    def test_lecturer_is_not_a_moderator(self):
        self.client.force_login(self.lecturer)
        self.assertEqual(self.client.get(reverse("moderation:queue")).status_code, 403)

    def test_approval_needs_post(self):
        r = self.make()
        self.client.force_login(self.mod)
        self.assertEqual(self.client.get(reverse("moderation:approve", args=[r.pk])).status_code, 405)

    @override_settings(RESOURCE_SCANNER="apps.resources.tests.FakeCleanScanner")
    def test_moderator_approves_clean_file(self):
        r = self.make()
        self.client.force_login(self.mod)
        resp = self.client.post(reverse("moderation:approve", args=[r.pk]))
        self.assertRedirects(resp, reverse("moderation:queue"))
        r.refresh_from_db()
        self.assertEqual((r.status, r.reviewed_by), (Resource.Status.APPROVED, self.mod))
        self.assertTrue(AuditLog.objects.filter(action="resource.approve", actor=self.mod).exists())

    @override_settings(ALLOW_APPROVE_WITHOUT_SCAN=False)
    def test_unscanned_file_cannot_be_approved_in_production_mode(self):
        r = self.make()  # no scanner -> unavailable
        with self.assertRaises(mod.ModerationError):
            mod.approve(r, self.mod)
        self.client.force_login(self.mod)
        self.client.post(reverse("moderation:approve", args=[r.pk]))
        r.refresh_from_db()
        self.assertEqual(r.status, Resource.Status.PENDING)

    @override_settings(ALLOW_APPROVE_WITHOUT_SCAN=True)
    def test_dev_mode_allows_unscanned_approval(self):
        r = self.make()
        mod.approve(r, self.mod)
        self.assertEqual(r.status, Resource.Status.APPROVED)

    def test_reject_requires_reason_and_notifies_via_status(self):
        r = self.make()
        with self.assertRaises(mod.ModerationError):
            mod.reject(r, self.mod, "  ")
        mod.reject(r, self.mod, "Not related to the course")
        r.refresh_from_db()
        self.assertEqual((r.status, r.rejection_reason), (Resource.Status.REJECTED, "Not related to the course"))
        self.assertTrue(AuditLog.objects.filter(action="resource.reject").exists())

    def test_hide_and_restore(self):
        r = self.make(status=Resource.Status.APPROVED)
        mod.hide(r, self.mod)
        self.assertEqual(r.status, Resource.Status.HIDDEN)
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(reverse("resources:detail", args=[r.pk])).status_code, 404)
        mod.restore(r, self.mod)
        self.assertEqual(r.status, Resource.Status.APPROVED)

    def test_cannot_approve_twice_or_approve_rejected(self):
        r = self.make(status=Resource.Status.REJECTED)
        with self.assertRaises(mod.ModerationError):
            mod.approve(r, self.mod)

    def test_queue_and_review_pages_render_for_moderator(self):
        r = self.make()
        self.client.force_login(self.mod)
        self.assertContains(self.client.get(reverse("moderation:queue")), "Sample notes")
        self.assertContains(self.client.get(reverse("moderation:review", args=[r.pk])), "Reject")

    def test_rescan_without_scanner_stays_unavailable(self):
        r = self.make()
        self.client.force_login(self.mod)
        self.client.post(reverse("moderation:rescan", args=[r.pk]))
        r.refresh_from_db()
        self.assertEqual(r.scan_status, Resource.ScanStatus.UNAVAILABLE)

    def test_audit_log_cannot_be_edited_in_admin(self):
        su = User.objects.create_superuser("root", "root@example.com", PW)
        self.client.force_login(su)
        self.make()
        entry = AuditLog.objects.first()
        self.assertEqual(self.client.get(reverse("admin:core_auditlog_change", args=[entry.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:core_auditlog_add")).status_code, 403)
        self.assertEqual(self.client.post(reverse("admin:core_auditlog_delete", args=[entry.pk]), {"post": "yes"}).status_code, 403)
