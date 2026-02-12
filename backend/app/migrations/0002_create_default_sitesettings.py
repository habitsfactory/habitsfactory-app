from django.db import migrations


def create_default_settings(apps, schema_editor):
    SiteSettings = apps.get_model("app", "SiteSettings")
    SiteSettings.objects.get_or_create(pk=1, defaults={"allow_registration": True})


def reverse(apps, schema_editor):
    SiteSettings = apps.get_model("app", "SiteSettings")
    SiteSettings.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_settings, reverse),
    ]
