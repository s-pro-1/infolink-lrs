from django.db import transaction

from .models import StudentCourseEnrollment


@transaction.atomic
def set_student_courses(student, courses):
    """Make the student's enrollments exactly match `courses`."""
    wanted = {c.id for c in courses}
    current = set(student.enrollments.values_list("course_id", flat=True))
    student.enrollments.filter(course_id__in=current - wanted).delete()
    StudentCourseEnrollment.objects.bulk_create(
        [StudentCourseEnrollment(student=student, course_id=cid) for cid in wanted - current])
