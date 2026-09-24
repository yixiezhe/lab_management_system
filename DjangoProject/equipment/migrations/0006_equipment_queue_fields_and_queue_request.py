from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("equipment", "0005_equipment_ball_mill_limit_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_allocate_window_days",
            field=models.PositiveSmallIntegerField(
                default=10,
                help_text="每次放榜时，最多向后分配多少天。",
                verbose_name="单次放榜分配天数",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_day_end_time",
            field=models.TimeField(
                default="22:00",
                help_text="排队分配的开始时间必须早于该时刻。",
                verbose_name="排队可分配开始时段终点",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_day_start_time",
            field=models.TimeField(
                default="07:00",
                help_text="排队分配的开始时间不得早于该时刻。",
                verbose_name="排队可分配开始时段起点",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_enabled",
            field=models.BooleanField(
                default=False,
                help_text="仅行星球磨机生效。启用后普通用户提交预约将进入排队，由系统统一分配。",
                verbose_name="启用排队机制",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_heavy_user_threshold_minutes",
            field=models.PositiveIntegerField(
                default=4320,
                help_text="滚动30天使用时长超过该阈值的用户，会被排到后层队列。",
                verbose_name="重度用户阈值(分钟/30天)",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_publish_time",
            field=models.TimeField(
                default="12:00",
                help_text="每日到达该时间后执行排队分配。",
                verbose_name="排队放榜时间",
            ),
        ),
        migrations.AddField(
            model_name="equipment",
            name="ball_mill_queue_request_window_days",
            field=models.PositiveSmallIntegerField(
                default=14,
                help_text="用户最多可提前多少天提交排队申请。",
                verbose_name="可提前提交排队天数",
            ),
        ),
        migrations.CreateModel(
            name="BallMillQueueRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_date", models.DateField(verbose_name="期望日期")),
                ("requested_start_time", models.TimeField(verbose_name="期望开始时间")),
                ("position_count", models.PositiveSmallIntegerField(default=1, verbose_name="需求工位数")),
                (
                    "operation_type",
                    models.CharField(
                        choices=[("grinding", "磨材料"), ("cleaning", "洗罐子")],
                        max_length=20,
                        verbose_name="操作类型",
                    ),
                ),
                ("rotation_speed_rpm", models.PositiveIntegerField(verbose_name="转速(r/min)")),
                ("milling_minutes", models.PositiveIntegerField(verbose_name="球磨时间(分钟)")),
                ("actual_duration_minutes", models.PositiveIntegerField(verbose_name="真实预约时长(分钟)")),
                ("remark", models.CharField(blank=True, default="", max_length=200, verbose_name="备注")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "排队中"),
                            ("allocated", "已分配"),
                            ("rejected", "未分配"),
                            ("cancelled", "已取消"),
                        ],
                        default="pending",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                ("fail_reason", models.CharField(blank=True, default="", max_length=200, verbose_name="失败原因")),
                ("allocated_start_at", models.DateTimeField(blank=True, null=True, verbose_name="分配开始时间")),
                ("allocated_end_at", models.DateTimeField(blank=True, null=True, verbose_name="分配结束时间")),
                ("allocated_position_nos", models.JSONField(blank=True, default=list, verbose_name="分配工位")),
                ("allocated_booking_ids", models.JSONField(blank=True, default=list, verbose_name="分配预约ID")),
                ("dispatched_at", models.DateTimeField(blank=True, null=True, verbose_name="放榜时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="申请时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                (
                    "equipment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ball_mill_queue_requests",
                        to="equipment.equipment",
                        verbose_name="仪器",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ball_mill_queue_requests",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="申请人",
                    ),
                ),
            ],
            options={
                "verbose_name": "球磨排队申请",
                "verbose_name_plural": "球磨排队申请",
                "ordering": ["created_at", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="ballmillqueuerequest",
            index=models.Index(
                fields=["equipment", "status", "requested_date", "requested_start_time"],
                name="equipment_b_equipme_3d9b43_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="ballmillqueuerequest",
            index=models.Index(
                fields=["equipment", "user", "status", "created_at"],
                name="equipment_b_equipme_8e065f_idx",
            ),
        ),
    ]

