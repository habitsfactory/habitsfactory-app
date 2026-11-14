from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("app", "0003_remove_sitesettings_allow_registration_invitelink"),
    ]

    operations = [
        migrations.AddField(
            model_name="habit",
            name="order",
            field=models.IntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name="habit",
            options={"ordering": ["order", "name"]},
        ),
    ]
