from django.db import migrations

VALID_TYPES = ["boolean", "counter", "value", "rating"]


def fix_invalid_types(apps, schema_editor):
    """CSV imports used to store a blank/unknown type; treat those as yes/no."""
    Habit = apps.get_model("app", "Habit")
    Habit.objects.exclude(habit_type__in=VALID_TYPES).update(habit_type="boolean")


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0004_habit_order"),
    ]

    operations = [
        migrations.RunPython(fix_invalid_types, migrations.RunPython.noop),
    ]
