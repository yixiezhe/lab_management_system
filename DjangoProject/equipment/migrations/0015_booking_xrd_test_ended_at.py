from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0014_equipment_xrd_remote_machine"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="xrd_test_ended_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="XRD测试结束时间",
            ),
        ),
    ]
