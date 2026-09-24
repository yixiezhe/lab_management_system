from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0015_booking_xrd_test_ended_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="xrd_tutorial_html",
            field=models.TextField(
                blank=True,
                default="The quick brown fox jumps over the lazy dog",
                help_text="仅 XRD 生效；前端教程窗口展示的 HTML 内容。",
                verbose_name="XRD使用教程HTML",
            ),
        ),
    ]
