from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("remote_access", "0005_rdpmachine_encrypted_device_secret"),
        ("equipment", "0013_xrd_booking_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="xrd_remote_machine",
            field=models.ForeignKey(
                blank=True,
                help_text="仅 XRD 生效；用户在本人预约时段内可通过该主机远程连接。",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="xrd_equipments",
                to="remote_access.rdpmachine",
                verbose_name="XRD远程主机",
            ),
        ),
    ]
