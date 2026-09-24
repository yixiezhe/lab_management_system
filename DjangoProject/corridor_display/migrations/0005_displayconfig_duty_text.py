from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("corridor_display", "0004_displayconfig_duty_rotation_unit"),
    ]

    operations = [
        migrations.AddField(
            model_name="displayconfig",
            name="duty_text",
            field=models.TextField(blank=True, default="", verbose_name="值日安排文本"),
        ),
    ]
