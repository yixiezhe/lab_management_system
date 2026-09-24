from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0007_equipment_direct_booking_window_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_publish_lead_days",
            field=models.PositiveSmallIntegerField(
                default=5,
                help_text="仅当排队申请的期望日期距离直约窗口边界不超过该天数时，才会在当日放榜中参与分配。",
                verbose_name="放榜提前天数",
            ),
        ),
    ]
