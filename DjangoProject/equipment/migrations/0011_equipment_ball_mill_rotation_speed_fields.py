from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0010_equipment_booking_allowed_users"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_max_rotation_speed_rpm",
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                help_text="仅行星球磨机生效，允许预约/排队时填写的最大转速；为空表示不限制。",
                null=True,
                verbose_name="最大转速(r/min)",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_min_rotation_speed_rpm",
            field=models.PositiveIntegerField(
                default=1,
                help_text="仅行星球磨机生效，允许预约/排队时填写的最小转速。",
                verbose_name="最小转速(r/min)",
            ),
        ),
    ]
