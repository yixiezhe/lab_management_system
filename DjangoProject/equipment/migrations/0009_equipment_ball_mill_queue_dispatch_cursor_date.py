from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0008_equipment_ball_mill_queue_publish_lead_days"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_dispatch_cursor_date",
            field=models.DateField(
                blank=True,
                default=None,
                help_text="分批放榜模式下“下一批分配窗口”的起始日期。为空时自动以当前直约窗口边界日期为起点。",
                null=True,
                verbose_name="排队放榜分配游标日期",
            ),
        ),
    ]
