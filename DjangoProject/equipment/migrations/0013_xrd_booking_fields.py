# Generated for XRD booking template

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0012_rename_equipment_b_equipme_3d9b43_idx_equipment_b_equipme_ceeb60_idx_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="equipment",
            name="booking_mode",
            field=models.CharField(
                choices=[
                    ("standard", "普通仪器"),
                    ("planetary_ball_mill", "行星球磨机"),
                    ("electrochemical_workstation", "输力强电化学工作站"),
                    ("xrd", "XRD"),
                ],
                default="standard",
                max_length=30,
                verbose_name="预约模式",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="xrd_measurement_mode",
            field=models.CharField(
                blank=True,
                choices=[("instant", "即时测"), ("in_situ", "原位")],
                default="",
                max_length=20,
                verbose_name="XRD测试方式",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="xrd_scan_speed",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=8,
                null=True,
                verbose_name="XRD扫速",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="xrd_scan_range_start",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=8,
                null=True,
                verbose_name="XRD扫描范围起点",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="xrd_scan_range_end",
            field=models.DecimalField(
                blank=True,
                decimal_places=3,
                max_digits=8,
                null=True,
                verbose_name="XRD扫描范围终点",
            ),
        ),
    ]
