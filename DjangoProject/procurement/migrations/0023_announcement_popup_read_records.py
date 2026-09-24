import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("procurement", "0022_purchaserequest_actual_payment_amount"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="globalannouncement",
            name="title",
            field=models.CharField(default="公告", max_length=120, verbose_name="公告标题"),
        ),
        migrations.AddField(
            model_name="globalannouncement",
            name="show_popup",
            field=models.BooleanField(default=False, verbose_name="登录时弹窗显示"),
        ),
        migrations.AddField(
            model_name="globalannouncement",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="created_announcements",
                to=settings.AUTH_USER_MODEL,
                verbose_name="发布人",
            ),
        ),
        migrations.AddField(
            model_name="globalannouncement",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="发布时间",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="globalannouncement",
            name="is_published",
            field=models.BooleanField(default=False, verbose_name="在首页展示"),
        ),
        migrations.AlterField(
            model_name="globalannouncement",
            name="updated_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="updated_announcements",
                to=settings.AUTH_USER_MODEL,
                verbose_name="最后修改人",
            ),
        ),
        migrations.AlterModelOptions(
            name="globalannouncement",
            options={
                "ordering": ["-created_at", "-id"],
                "verbose_name": "公告",
                "verbose_name_plural": "公告",
            },
        ),
        migrations.CreateModel(
            name="AnnouncementRead",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("read_at", models.DateTimeField(auto_now=True, verbose_name="阅读时间")),
                (
                    "announcement",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="read_records",
                        to="procurement.globalannouncement",
                        verbose_name="公告",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="announcement_reads",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户",
                    ),
                ),
            ],
            options={
                "verbose_name": "公告阅读记录",
                "verbose_name_plural": "公告阅读记录",
                "ordering": ["-read_at"],
                "unique_together": {("announcement", "user")},
            },
        ),
    ]
