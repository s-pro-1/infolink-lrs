from django.db import migrations
from django.utils.text import slugify

DEFAULTS = [
    "Lecture Notes", "Assignments", "Past Examinations", "Tutorials",
    "Presentations", "Reference Materials", "Study Guides", "Other",
]


def add_categories(apps, schema_editor):
    Category = apps.get_model("resources", "ResourceCategory")
    for name in DEFAULTS:
        Category.objects.get_or_create(name=name, defaults={"slug": slugify(name)})


class Migration(migrations.Migration):
    dependencies = [("resources", "0001_initial")]
    operations = [migrations.RunPython(add_categories, migrations.RunPython.noop)]
