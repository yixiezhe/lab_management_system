# Generated manually for the group affairs module.

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import group_affairs.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GroupAffairBoard",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("text_content", models.TextField(blank=True, verbose_name="事务文本")),
                ("duty_schedule", models.JSONField(default=group_affairs.models.default_duty_schedule, verbose_name="值日表")),
                ("duty_reminder_enabled", models.BooleanField(default=False, verbose_name="启用每日值日弹窗提醒")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="最后更新时间")),
                ("tutor", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="group_affair_board", to=settings.AUTH_USER_MODEL, verbose_name="导师")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_group_affair_boards", to=settings.AUTH_USER_MODEL, verbose_name="最后修改人")),
            ],
            options={
                "verbose_name": "小组事务板",
                "verbose_name_plural": "小组事务板",
                "ordering": ["tutor__name", "id"],
            },
        ),
        migrations.CreateModel(
            name="GroupAffairNotice",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(default="小组提醒", max_length=120, verbose_name="提醒标题")),
                ("content", models.TextField(verbose_name="提醒内容")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="发布时间")),
                ("board", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notices", to="group_affairs.groupaffairboard", verbose_name="小组事务板")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_group_affair_notices", to=settings.AUTH_USER_MODEL, verbose_name="发布人")),
            ],
            options={
                "verbose_name": "小组事务弹窗提醒",
                "verbose_name_plural": "小组事务弹窗提醒",
                "ordering": ["-created_at", "-id"],
            },
        ),
        migrations.CreateModel(
            name="GroupAffairAdmin",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="任命时间")),
                ("assigned_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_group_affair_admins", to=settings.AUTH_USER_MODEL, verbose_name="任命人")),
                ("tutor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_affair_admin_groups", to=settings.AUTH_USER_MODEL, verbose_name="导师")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_affair_adminships", to=settings.AUTH_USER_MODEL, verbose_name="小组管理员")),
            ],
            options={
                "verbose_name": "小组事务管理员",
                "verbose_name_plural": "小组事务管理员",
                "ordering": ["tutor__name", "user__name", "id"],
                "unique_together": {("tutor", "user")},
            },
        ),
        migrations.CreateModel(
            name="GroupAffairNoticeRead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("read_at", models.DateTimeField(auto_now=True, verbose_name="阅读时间")),
                ("notice", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="read_records", to="group_affairs.groupaffairnotice", verbose_name="提醒")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_affair_notice_reads", to=settings.AUTH_USER_MODEL, verbose_name="用户")),
            ],
            options={
                "verbose_name": "小组事务提醒阅读记录",
                "verbose_name_plural": "小组事务提醒阅读记录",
                "ordering": ["-read_at"],
                "unique_together": {("notice", "user")},
            },
        ),
        migrations.CreateModel(
            name="GroupAffairDutyReminderRead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("duty_date", models.DateField(verbose_name="值日日期")),
                ("read_at", models.DateTimeField(auto_now=True, verbose_name="提醒确认时间")),
                ("board", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="duty_reminder_reads", to="group_affairs.groupaffairboard", verbose_name="小组事务板")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_affair_duty_reminder_reads", to=settings.AUTH_USER_MODEL, verbose_name="用户")),
            ],
            options={
                "verbose_name": "小组值日提醒确认记录",
                "verbose_name_plural": "小组值日提醒确认记录",
                "ordering": ["-duty_date", "-read_at"],
                "unique_together": {("board", "user", "duty_date")},
            },
        ),
    ]
