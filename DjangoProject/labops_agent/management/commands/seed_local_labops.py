import json
import os
from getpass import getpass
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from equipment.models import Equipment
from procurement.models import GlobalAnnouncement, Platform, WhitelistItem
from users.models import Role, UserProfile


SAFE_EQUIPMENT_FIELDS = {
    "location",
    "description",
    "booking_mode",
    "time_unit_minutes",
    "open_time_start",
    "open_time_end",
    "max_advance_days",
    "ball_mill_duration_unit_minutes",
    "ball_mill_min_rotation_speed_rpm",
    "ball_mill_max_rotation_speed_rpm",
    "ball_mill_max_actual_minutes",
    "ball_mill_monthly_max_actual_minutes",
    "ball_mill_queue_enabled",
    "ball_mill_queue_publish_time",
    "ball_mill_queue_request_window_days",
    "ball_mill_queue_allocate_window_days",
    "ball_mill_queue_dispatch_cursor_date",
    "ball_mill_queue_publish_lead_days",
    "ball_mill_queue_day_start_time",
    "ball_mill_queue_day_end_time",
    "ball_mill_queue_heavy_user_threshold_minutes",
    "ball_mill_direct_booking_window_days",
    "ball_mill_direct_booking_cutoff_time",
    "electrochemical_offline_channels",
    "xrd_tutorial_html",
    "early_bird_max_advance_days",
    "is_active",
}


class Command(BaseCommand):
    help = "把脱敏后的远端配置种子导入本地开发数据库"

    def add_arguments(self, parser):
        parser.add_argument("--fixture", required=True)
        parser.add_argument("--admin-username", default="localadmin")
        parser.add_argument("--admin-password", default=None, help="Prefer LABOPS_DEMO_ADMIN_PASSWORD or an interactive prompt.")

    def handle(self, *args, **options):
        password = options["admin_password"] or os.getenv("LABOPS_DEMO_ADMIN_PASSWORD")
        if not password:
            password = getpass("Demo admin password (no default): ")
        if len(password) < 12:
            raise CommandError("Use a demo admin password with at least 12 characters.")
        path = Path(options["fixture"]).resolve(strict=True)
        if path.stat().st_size > 5 * 1024 * 1024:
            raise CommandError("种子文件异常，超过 5 MB。")
        try:
            rows = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, UnicodeError) as exc:
            raise CommandError("种子文件不是有效 UTF-8 JSON。") from exc
        if not isinstance(rows, list):
            raise CommandError("种子文件顶层必须是列表。")

        counts = {"whitelist": 0, "platform": 0, "equipment": 0, "announcement": 0}
        with transaction.atomic():
            for row in rows:
                model = row.get("model")
                fields = row.get("fields") or {}
                if model == "procurement.whitelistitem":
                    content = str(fields.get("content") or "").strip()
                    if not content:
                        continue
                    defaults = {
                        key: fields.get(key)
                        for key in (
                            "main_category",
                            "platform",
                            "purchase_type",
                            "manufacturer",
                            "cas_number",
                            "product_number",
                            "parameters",
                            "specifications",
                        )
                    }
                    WhitelistItem.objects.update_or_create(content=content, defaults=defaults)
                    counts["whitelist"] += 1
                elif model == "procurement.platform":
                    name = str(fields.get("name") or "").strip()
                    if not name:
                        continue
                    Platform.objects.update_or_create(
                        name=name,
                        defaults={
                            "prefix": fields.get("prefix"),
                            "category": fields.get("category"),
                        },
                    )
                    counts["platform"] += 1
                elif model == "equipment.equipment":
                    name = str(fields.get("name") or "").strip()
                    if not name:
                        continue
                    defaults = {
                        key: fields.get(key)
                        for key in SAFE_EQUIPMENT_FIELDS
                        if key in fields
                    }
                    defaults["xrd_remote_machine"] = None
                    equipment, _ = Equipment.objects.update_or_create(
                        name=name, defaults=defaults
                    )
                    equipment.early_bird_users.clear()
                    equipment.booking_allowed_users.clear()
                    counts["equipment"] += 1
                elif model == "procurement.globalannouncement" and fields.get(
                    "is_published"
                ):
                    title = str(fields.get("title") or "公告").strip() or "公告"
                    GlobalAnnouncement.objects.update_or_create(
                        title=title,
                        defaults={
                            "content": fields.get("content") or "",
                            "is_published": True,
                            "show_popup": bool(fields.get("show_popup")),
                        },
                    )
                    counts["announcement"] += 1

            admin, _ = UserProfile.objects.get_or_create(
                username=options["admin_username"],
                defaults={
                    "name": "本地 RAG 管理员",
                    "email": "localadmin@example.invalid",
                    "is_staff": True,
                    "is_superuser": True,
                },
            )
            admin.name = "本地 RAG 管理员"
            admin.email = "localadmin@example.invalid"
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password(password)
            admin.save()
            role, _ = Role.objects.get_or_create(name="系统管理员")
            admin.roles.add(role)

        self.stdout.write(
            self.style.SUCCESS(
                "本地种子导入完成："
                + ", ".join(f"{key}={value}" for key, value in counts.items())
            )
        )
