from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0006_equipment_queue_fields_and_queue_request"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_direct_booking_cutoff_time",
            field=models.TimeField(
                default="07:00",
                help_text="窗口边界时刻（如第8天 07:00 之后走排队）。",
                verbose_name="直约窗口截止时刻",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_direct_booking_window_days",
            field=models.PositiveSmallIntegerField(
                default=7,
                help_text="开始时间落在该窗口内可直接预约；超过窗口走排队。",
                verbose_name="直约窗口天数",
            ),
        ),
    ]

