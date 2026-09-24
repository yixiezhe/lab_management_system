from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Feedback",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("bug", "系统 Bug"),
                            ("suggestion", "功能建议"),
                            ("other", "其他反馈"),
                        ],
                        default="bug",
                        max_length=20,
                        verbose_name="反馈类型",
                    ),
                ),
                ("content", models.TextField(verbose_name="反馈内容")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="提交时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("admin_reply", models.TextField(blank=True, default="", verbose_name="管理员回复")),
                ("replied_at", models.DateTimeField(blank=True, null=True, verbose_name="回复时间")),
                (
                    "replied_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="feedback_replies",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="回复管理员",
                    ),
                ),
            ],
            options={
                "verbose_name": "反馈和建议",
                "verbose_name_plural": "反馈和建议",
                "ordering": ["-created_at"],
            },
        ),
    ]
