from datetime import time as dt_time

from django.core.management.base import BaseCommand
from django.db import transaction

from equipment.models import Equipment, BallMillQueueRequest
from equipment.time_control import get_controlled_now
from equipment.views import (
    build_aware_datetime,
    get_dispatch_publish_open_at,
    get_pending_dispatch_window,
    sort_queue_requests_for_dispatch,
    try_allocate_single_queue_request,
)


class Command(BaseCommand):
    help = "执行行星球磨机排队放榜分配"

    def add_arguments(self, parser):
        parser.add_argument("--equipment-id", type=int, default=None, help="仅处理指定仪器 ID")
        parser.add_argument("--force", action="store_true", help="忽略放榜时间限制，立即执行")

    def handle(self, *args, **options):
        force = options["force"]
        equipment_id = options["equipment_id"]
        now = get_controlled_now()

        queryset = Equipment.objects.filter(
            booking_mode=Equipment.BOOKING_MODE_PLANETARY_BALL_MILL,
            ball_mill_queue_enabled=True,
            is_active=True,
        ).order_by("id")
        if equipment_id:
            queryset = queryset.filter(id=equipment_id)

        total_allocated = 0
        total_pending = 0
        total_rolled_over = 0
        total_skipped = 0

        for equipment in queryset:
            with transaction.atomic():
                locked_equipment = Equipment.objects.select_for_update().get(pk=equipment.pk)
                dispatch_window_start_date, dispatch_window_end_date = get_pending_dispatch_window(
                    locked_equipment,
                    anchor=now,
                )
                publish_open_at = get_dispatch_publish_open_at(
                    locked_equipment,
                    dispatch_window_start_date,
                )
                publish_open_date = publish_open_at.date()
                publish_request_date_cutoff = dispatch_window_end_date

                if not force and now < publish_open_at:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[设备 {locked_equipment.id}] 当前批次需在 "
                            f"{publish_open_at.strftime('%Y-%m-%d %H:%M')} 后放榜；已跳过。"
                        )
                    )
                    continue

                allocation_start_at = build_aware_datetime(
                    dispatch_window_start_date,
                    locked_equipment.ball_mill_queue_day_start_time,
                )
                allocation_end_at = build_aware_datetime(publish_request_date_cutoff, dt_time.max)
                pending_requests = list(
                    BallMillQueueRequest.objects.filter(
                        equipment=locked_equipment,
                        status=BallMillQueueRequest.STATUS_PENDING,
                        requested_date__lte=dispatch_window_end_date,
                    )
                    .select_related("user")
                    .order_by("created_at", "id")
                )
                if not pending_requests:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[设备 {locked_equipment.id}] 当前无可放榜排队申请；"
                            f"批次窗口 {dispatch_window_start_date.strftime('%Y-%m-%d')}"
                            f"~{dispatch_window_end_date.strftime('%Y-%m-%d')}。"
                        )
                    )
                    continue

                ordered = sort_queue_requests_for_dispatch(locked_equipment, pending_requests)

                allocated_count = 0
                rolled_over_count = 0
                skipped_count = 0
                for queue_request in ordered:
                    allocated = try_allocate_single_queue_request(
                        queue_request,
                        allocation_end_at,
                        allocation_start_at=allocation_start_at,
                        roll_over_on_failure=True,
                        current_window_end_date=dispatch_window_end_date,
                    )
                    if allocated:
                        allocated_count += 1
                    elif queue_request.status == BallMillQueueRequest.STATUS_PENDING:
                        rolled_over_count += 1
                    else:
                        skipped_count += 1

                next_dispatch_window_start_date = locked_equipment.advance_ball_mill_queue_dispatch_cursor(
                    publish_request_date_cutoff
                )
            total_pending += len(ordered)
            total_allocated += allocated_count
            total_rolled_over += rolled_over_count
            total_skipped += skipped_count
            self.stdout.write(
                self.style.SUCCESS(
                    f"[设备 {equipment.id}] 批次窗口 {dispatch_window_start_date.strftime('%Y-%m-%d')}"
                    f"~{dispatch_window_end_date.strftime('%Y-%m-%d')}（开放日 {publish_open_date.strftime('%Y-%m-%d')}；"
                    f"截止 {publish_request_date_cutoff.strftime('%Y-%m-%d')}）；"
                    f"排队{len(ordered)}条，已分配{allocated_count}条，顺延{rolled_over_count}条，未分配{skipped_count}条；"
                    f"下一批起始 {next_dispatch_window_start_date.strftime('%Y-%m-%d')}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"完成：待分配{total_pending}条，已分配{total_allocated}条，"
                f"顺延{total_rolled_over}条，未分配{total_skipped}条"
            )
        )
