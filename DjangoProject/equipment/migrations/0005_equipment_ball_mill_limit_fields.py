from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0004_equipment_booking_mode_and_ball_mill_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_max_actual_minutes",
            field=models.PositiveIntegerField(
                default=2880,
                help_text="仅行星球磨机生效，单次预约真实时长上限。",
                verbose_name="单次最大真实预约时长(分钟)",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_monthly_max_actual_minutes",
            field=models.PositiveIntegerField(
                blank=True,
                default=None,
                help_text="仅行星球磨机生效，按用户统计的每月累计真实预约时长上限；为空表示不限制。",
                null=True,
                verbose_name="每月最大真实预约时长(分钟)",
            ),
        ),
    ]

