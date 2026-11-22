"""Create SAMPLE academic data for development only.

Everything created here is placeholder data. It is NOT real Infolink
information; administrators should replace it with the real structure.
"""
from django.core.management.base import BaseCommand

from apps.academics.models import (AcademicProgram, AcademicYear, Campus, Course,
                                   Department, Semester)

SAMPLE = "[SAMPLE] "


class Command(BaseCommand):
    help = "Load clearly labelled sample academic data for development."

    def handle(self, *args, **opts):
        campus, _ = Campus.objects.get_or_create(name="Hawassa", defaults={"city": "Hawassa"})
        dept, _ = Department.objects.get_or_create(campus=campus, name=SAMPLE + "Computer Science")
        AcademicProgram.objects.get_or_create(department=dept, name=SAMPLE + "BSc Computer Science")
        year, _ = AcademicYear.objects.get_or_create(label=SAMPLE + "Year A", defaults={"is_current": True})
        Semester.objects.get_or_create(academic_year=year, name="Semester I", defaults={"is_current": True})
        Semester.objects.get_or_create(academic_year=year, name="Semester II")
        for code, title, level in [
            ("SAMP101", "Introduction to Programming", 1),
            ("SAMP201", "Database Systems", 2),
            ("SAMP202", "Data Structures", 2),
            ("SAMP301", "Computer Networks", 3),
        ]:
            course, _ = Course.objects.get_or_create(
                department=dept, code=code, defaults={"title": SAMPLE + title, "level": level})
            course.programs.set(AcademicProgram.objects.filter(department=dept))
        self.stdout.write(self.style.SUCCESS("Sample academic data loaded (labelled [SAMPLE])."))
