from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0005_fix_invalid_habit_types"),
    ]

    operations = [
        migrations.AlterField(
            model_name="habit",
            name="habit_type",
            field=models.CharField(
                choices=[
                    ("boolean", "Yes/No"),
                    ("counter", "Counter"),
                    ("value", "Decimal Value"),
                    ("rating", "Rating"),
                    ("percentage", "Percentage"),
                ],
                default="boolean",
                max_length=10,
            ),
        ),
    ]
