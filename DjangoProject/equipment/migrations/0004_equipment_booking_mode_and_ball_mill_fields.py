from datetime import datetime

from django.db import migrations, models
from django.utils import timezone


def backfill_booking_datetimes(apps, schema_editor):
    Booking = apps.get_model("equipment", "Booking")
    tz = timezone.get_default_timezone()

    for booking in Booking.objects.all().iterator():
        if booking.date and booking.start_time:
            booking.start_at = timezone.make_aware(
                datetime.combine(booking.date, booking.start_time),
                tz,
            )
        if booking.date and booking.end_time:
            booking.end_at = timezone.make_aware(
                datetime.combine(booking.date, booking.end_time),
                tz,
            )
        if booking.start_time and booking.end_time:
            start_minutes = booking.start_time.hour * 60 + booking.start_time.minute
            end_minutes = booking.end_time.hour * 60 + booking.end_time.minute
            booking.actual_duration_minutes = max(end_minutes - start_minutes, 0)
        booking.save(
            update_fields=[
                "start_at",
                "end_at",
                "actual_duration_minutes",
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0003_equipment_early_bird_max_advance_days_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_duration_unit_minutes",
            field=models.PositiveSmallIntegerField(
                default=12,
                help_text="仅行星球磨机生效，用户输入球磨时间时需按此粒度对齐。",
                verbose_name="球磨时间粒度(分钟)",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="booking_mode",
            field=models.CharField(
                choices=[("standard", "普通仪器"), ("planetary_ball_mill", "行星球磨机")],
                default="standard",
                max_length=30,
                verbose_name="预约模式",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="actual_duration_minutes",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="真实预约时长(分钟)"),
        ),
        migrations.AddField(
            model_name="booking",
            name="end_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="结束时间点"),
        ),
        migrations.AddField(
            model_name="booking",
            name="milling_minutes",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="球磨时间(分钟)"),
        ),
        migrations.AddField(
            model_name="booking",
            name="operation_type",
            field=models.CharField(
                blank=True,
                choices=[("grinding", "磨材料"), ("cleaning", "洗罐子")],
                default="",
                max_length=20,
                verbose_name="操作类型",
            ),
        ),
        migrations.AddField(
            model_name="booking",
            name="position_no",
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="工位号"),
        ),
        migrations.AddField(
            model_name="booking",
            name="rotation_speed_rpm",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="转速(r/min)"),
        ),
        migrations.AddField(
            model_name="booking",
            name="start_at",
            field=models.DateTimeField(blank=True, null=True, verbose_name="开始时间点"),
        ),
        migrations.RunPython(backfill_booking_datetimes, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name="booking",
            index=models.Index(
                fields=["equipment", "status", "start_at", "end_at"],
                name="equipment_window_idx",
            ),
        ),
    ]
