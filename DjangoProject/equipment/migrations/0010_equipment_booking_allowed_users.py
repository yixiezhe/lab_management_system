from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0009_equipment_ball_mill_queue_dispatch_cursor_date"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="booking_allowed_users",
            field=models.ManyToManyField(
                blank=True,
                help_text="为空表示所有登录用户均可预约；设置后仅选中的用户可预约或提交排队申请。",
                related_name="booking_allowed_equipments",
                to=settings.AUTH_USER_MODEL,
                verbose_name="可预约用户",
            ),
        ),
    ]
