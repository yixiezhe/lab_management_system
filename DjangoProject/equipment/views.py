import base64
import csv
from calendar import monthrange
from datetime import datetime, timedelta, time as dt_time
from urllib.parse import quote

from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import HttpResponse
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Equipment, Booking, BallMillQueueRequest
from .serializers import (
    EquipmentSerializer,
    BookingSerializer,
    BookingCreateSerializer,
    BallMillQueueRequestSerializer,
    BallMillQueueRequestCreateSerializer,
)
from .permissions import IsSystemAdmin, IsSystemAdminOrTutor
from .time_control import clear_test_now, get_controlled_now, get_controlled_today, get_test_now, set_test_now

User = get_user_model()


def get_user_display_name(user):
    return getattr(user, "name", None) or getattr(user, "username", "") or getattr(user, "email", "")


def booking_user_scope_error_message():
    return "你不在该设备的可预约用户范围内。"


def parse_date_or_today(date_str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        return get_controlled_today()


def parse_month_or_current(month_str):
    try:
        return datetime.strptime(month_str, "%Y-%m").date().replace(day=1)
    except Exception:
        return get_controlled_today().replace(day=1)


def parse_time_or_none(time_str):
    if not time_str:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(time_str, fmt).time()
        except ValueError:
            continue
    return None


def parse_test_datetime_or_none(dt_text):
    if not dt_text:
        return None

    if isinstance(dt_text, datetime):
        parsed = dt_text
    else:
        text = str(dt_text).strip()
        if not text:
            return None
        parsed = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                return None

    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return timezone.localtime(parsed)


def build_day_window(the_date):
    tz = timezone.get_current_timezone()
    day_start = timezone.make_aware(datetime.combine(the_date, dt_time.min), tz)
    day_end = day_start + timedelta(days=1)
    return day_start, day_end


def build_month_window(month_start):
    _, last_day = monthrange(month_start.year, month_start.month)
    month_end = month_start.replace(day=last_day)
    tz = timezone.get_current_timezone()
    month_start_at = timezone.make_aware(datetime.combine(month_start, dt_time.min), tz)
    month_end_at = timezone.make_aware(datetime.combine(month_end + timedelta(days=1), dt_time.min), tz)
    return month_start_at, month_end_at, month_end


def ceil_to_next_hour(aware_dt):
    localized = timezone.localtime(aware_dt)
    if localized.minute == 0 and localized.second == 0 and localized.microsecond == 0:
        return localized
    return localized.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


def build_booking_summary(booking):
    return {
        "id": booking.id,
        "position_no": booking.position_no,
        "booked_by": get_user_display_name(booking.user),
        "rotation_speed_rpm": booking.rotation_speed_rpm,
        "operation_type": booking.operation_type,
        "operation_type_display": booking.get_operation_type_display() if booking.operation_type else "",
        "start_at": timezone.localtime(booking.start_at).isoformat() if booking.start_at else "",
        "end_at": timezone.localtime(booking.end_at).isoformat() if booking.end_at else "",
    }


def describe_ball_mill_window(equipment, start_at, end_at, requested_speed_rpm):
    overlapping_bookings = list(
        Booking.objects.filter(
            equipment=equipment,
            status="active",
            start_at__lt=end_at,
            end_at__gt=start_at,
        )
        .select_related("user")
        .order_by("start_at", "position_no")
    )

    speeds = {booking.rotation_speed_rpm for booking in overlapping_bookings if booking.rotation_speed_rpm}
    inconsistent_speed = len(speeds) > 1
    locked_speed_rpm = next(iter(speeds), None) if len(speeds) == 1 else None
    occupied_by_position = {
        booking.position_no: booking
        for booking in overlapping_bookings
        if booking.position_no
    }

    positions = []
    allowed_positions = []
    for position_no in range(1, equipment.get_ball_mill_position_count() + 1):
        existing_booking = occupied_by_position.get(position_no)
        if existing_booking:
            positions.append(
                {
                    "position_no": position_no,
                    "status": "occupied",
                    "allowed": False,
                    "reason": (
                        f"{get_user_display_name(existing_booking.user)} 已预约，"
                        f"转速 {existing_booking.rotation_speed_rpm or '-'} r/min"
                    ),
                    "booking": build_booking_summary(existing_booking),
                }
            )
            continue

        if inconsistent_speed:
            positions.append(
                {
                    "position_no": position_no,
                    "status": "data_conflict",
                    "allowed": False,
                    "reason": "当前时段存在多种转速的历史预约，请联系管理员处理。",
                    "booking": None,
                }
            )
            continue

        if locked_speed_rpm and requested_speed_rpm and requested_speed_rpm != locked_speed_rpm:
            positions.append(
                {
                    "position_no": position_no,
                    "status": "speed_locked",
                    "allowed": False,
                    "reason": f"当前时段转速已锁定为 {locked_speed_rpm} r/min。",
                    "booking": None,
                }
            )
            continue

        reason = "可预约"
        if locked_speed_rpm:
            reason = f"可预约，且需保持 {locked_speed_rpm} r/min"

        position_data = {
            "position_no": position_no,
            "status": "available",
            "allowed": True,
            "reason": reason,
            "booking": None,
        }
        positions.append(position_data)
        allowed_positions.append(position_no)

    if inconsistent_speed:
        summary = "当前时段存在多种转速的历史预约，已禁止继续预约。"
    elif locked_speed_rpm and requested_speed_rpm and requested_speed_rpm != locked_speed_rpm:
        summary = f"当前时段已锁定为 {locked_speed_rpm} r/min，仅可预约相同转速的空闲工位。"
    elif allowed_positions:
        summary = f"可预约工位：{', '.join(str(position) for position in allowed_positions)} 号位"
    else:
        summary = "当前时段已无可用工位。"

    return {
        "locked_speed_rpm": locked_speed_rpm,
        "inconsistent_speed": inconsistent_speed,
        "allowed_positions": allowed_positions,
        "positions": positions,
        "overlapping_bookings": [build_booking_summary(booking) for booking in overlapping_bookings],
        "summary": summary,
    }


def build_ball_mill_hour_windows(equipment, the_date, requested_milling_minutes, requested_speed_rpm):
    tz = timezone.get_current_timezone()
    actual_duration_minutes = equipment.calculate_ball_mill_actual_minutes(requested_milling_minutes)
    now = get_controlled_now()
    is_history_day = the_date < now.date()

    hour_windows = []
    for hour in range(24):
        start_at = timezone.make_aware(datetime.combine(the_date, dt_time(hour, 0)), tz)
        end_at = start_at + timedelta(minutes=actual_duration_minutes)
        window_state = describe_ball_mill_window(
            equipment,
            start_at,
            end_at,
            requested_speed_rpm,
        )
        is_past = is_history_day or end_at <= now
        occupied_count = len(window_state["overlapping_bookings"])
        is_full = occupied_count >= equipment.get_ball_mill_position_count()

        if is_past:
            card_status = "past"
            summary = "历史日期或当前时间之前不可预约。"
        elif is_full:
            card_status = "full"
            summary = "4 个工位均已被占用。"
        elif occupied_count > 0:
            card_status = "partial"
            summary = (
                f"已有 {occupied_count} 个工位被占用；"
                f"剩余工位仅可预约 {window_state['locked_speed_rpm'] or '-'} r/min。"
            )
        else:
            card_status = "available"
            summary = "4 个工位均可预约。"

        positions = []
        for position in window_state["positions"]:
            position_data = dict(position)
            if is_past:
                position_data["allowed"] = False
                if position_data.get("booking"):
                    position_data["status"] = "occupied"
                else:
                    position_data["status"] = "past"
                    position_data["reason"] = "历史日期或当前时间之前不可预约。"
            positions.append(position_data)

        hour_windows.append(
            {
                "start": timezone.localtime(start_at).strftime("%H:%M"),
                "hour_label": f"{hour:02d}:00",
                "start_at": timezone.localtime(start_at).isoformat(),
                "end_at": timezone.localtime(end_at).isoformat(),
                "actual_duration_minutes": actual_duration_minutes,
                "locked_speed_rpm": window_state["locked_speed_rpm"],
                "occupied_count": occupied_count,
                "is_past": is_past,
                "is_full": is_full,
                "card_status": card_status,
                "summary": summary if not window_state["inconsistent_speed"] else "当前时段存在多种转速历史数据，暂不可预约。",
                "positions": positions,
            }
        )

    return hour_windows


def build_electrochemical_channel_options(equipment):
    offline_channels = equipment.get_electrochemical_offline_channel_set()
    channels = []
    for channel_no in range(1, equipment.get_electrochemical_channel_count() + 1):
        channels.append(
            {
                "channel_no": channel_no,
                "name": f"通道{channel_no}",
                "offline": channel_no in offline_channels,
            }
        )
    return channels, offline_channels


def parse_channel_no_or_none(raw_value):
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def build_aware_datetime(date_value, time_value):
    tz = timezone.get_current_timezone()
    return timezone.make_aware(datetime.combine(date_value, time_value), tz)


def get_week_monday(date_value):
    return date_value - timedelta(days=date_value.weekday())


def get_queue_request_batch_window(requested_date):
    start_date = get_week_monday(requested_date)
    return start_date, start_date + timedelta(days=6)


def get_pending_dispatch_window(equipment, anchor=None):
    earliest_pending_date = (
        BallMillQueueRequest.objects.filter(
            equipment=equipment,
            status=BallMillQueueRequest.STATUS_PENDING,
        )
        .order_by("requested_date", "created_at", "id")
        .values_list("requested_date", flat=True)
        .first()
    )
    if earliest_pending_date:
        return get_queue_request_batch_window(earliest_pending_date)
    return equipment.get_ball_mill_queue_dispatch_window(anchor=anchor, use_cursor=True)


def get_dispatch_publish_open_at(equipment, dispatch_window_start_date):
    publish_open_date = dispatch_window_start_date - timedelta(days=5)
    return build_aware_datetime(
        publish_open_date,
        equipment.ball_mill_queue_publish_time or dt_time.min,
    )


def roll_queue_request_to_next_batch(queue_request, current_window_end_date):
    next_window_start_date = current_window_end_date + timedelta(days=1)
    next_window_end_date = next_window_start_date + timedelta(days=6)
    weekday_offset = queue_request.requested_date.weekday()
    queue_request.status = BallMillQueueRequest.STATUS_PENDING
    queue_request.requested_date = next_window_start_date + timedelta(days=weekday_offset)
    queue_request.requested_start_time = queue_request.equipment.ball_mill_queue_day_start_time
    queue_request.fail_reason = (
        f"本批次容量不足，已顺延至 "
        f"{next_window_start_date.strftime('%Y-%m-%d')} - {next_window_end_date.strftime('%Y-%m-%d')}。"
    )
    queue_request.allocated_start_at = None
    queue_request.allocated_end_at = None
    queue_request.allocated_position_nos = []
    queue_request.allocated_booking_ids = []
    queue_request.dispatched_at = get_controlled_now()
    queue_request.save(
        update_fields=[
            "status",
            "requested_date",
            "requested_start_time",
            "fail_reason",
            "allocated_start_at",
            "allocated_end_at",
            "allocated_position_nos",
            "allocated_booking_ids",
            "dispatched_at",
            "updated_at",
        ]
    )
    return next_window_start_date, next_window_end_date


def clip_user_usage_minutes_in_range(equipment, user, range_start, range_end):
    qs = Booking.objects.filter(
        equipment=equipment,
        user=user,
        status="active",
        start_at__lt=range_end,
        end_at__gt=range_start,
    )
    minutes = 0
    for booking in qs:
        overlap_start = max(booking.start_at, range_start)
        overlap_end = min(booking.end_at, range_end)
        if overlap_end > overlap_start:
            minutes += int((overlap_end - overlap_start).total_seconds() // 60)
    return minutes


def get_recent_30d_usage_window_end(equipment, anchor=None):
    if equipment.is_planetary_ball_mill() and equipment.ball_mill_queue_enabled:
        return equipment.get_ball_mill_direct_booking_cutoff(anchor=anchor)
    return get_controlled_now(anchor=anchor)


def get_queue_priority_usage_window_end(equipment, anchor=None):
    if equipment.is_planetary_ball_mill() and equipment.ball_mill_queue_enabled:
        _, dispatch_window_end_date = get_pending_dispatch_window(equipment, anchor=anchor)
        return build_aware_datetime(dispatch_window_end_date + timedelta(days=1), dt_time.min)
    return get_recent_30d_usage_window_end(equipment, anchor=anchor)


def get_queue_priority_usage_window(equipment, anchor=None):
    window_end = get_queue_priority_usage_window_end(equipment, anchor=anchor)
    return window_end - timedelta(days=30), window_end


def get_recent_30d_usage_window(equipment, anchor=None):
    window_end = get_recent_30d_usage_window_end(equipment, anchor=anchor)
    return window_end - timedelta(days=30), window_end


def get_recent_30d_usage_minutes(equipment, user, anchor=None):
    window_start, window_end = get_recent_30d_usage_window(equipment, anchor=anchor)
    return clip_user_usage_minutes_in_range(equipment, user, window_start, window_end)


def get_queue_priority_usage_minutes(equipment, user, anchor=None):
    window_start, window_end = get_queue_priority_usage_window(equipment, anchor=anchor)
    return clip_user_usage_minutes_in_range(equipment, user, window_start, window_end)


def get_month_window_start(aware_dt):
    local = timezone.localtime(aware_dt)
    month_start_date = local.date().replace(day=1)
    return build_aware_datetime(month_start_date, dt_time.min)


def get_next_month_start(month_start_at):
    local = timezone.localtime(month_start_at)
    if local.month == 12:
        next_date = local.date().replace(year=local.year + 1, month=1, day=1)
    else:
        next_date = local.date().replace(month=local.month + 1, day=1)
    return build_aware_datetime(next_date, dt_time.min)


def month_limit_allows(equipment, user, start_at, duration_minutes):
    limit = equipment.ball_mill_monthly_max_actual_minutes
    if not limit:
        return True
    month_start_at = get_month_window_start(start_at)
    month_end_at = get_next_month_start(month_start_at)
    used = clip_user_usage_minutes_in_range(equipment, user, month_start_at, month_end_at)
    return used + duration_minutes <= limit


def ceil_to_next_full_hour(aware_dt):
    local = timezone.localtime(aware_dt)
    floored = local.replace(minute=0, second=0, microsecond=0)
    if local == floored:
        return floored
    return floored + timedelta(hours=1)


def normalize_queue_candidate_start(equipment, candidate_start):
    local = ceil_to_next_full_hour(candidate_start)
    current_date = timezone.localtime(local).date()
    day_start_at = build_aware_datetime(current_date, equipment.ball_mill_queue_day_start_time)
    day_end_at = build_aware_datetime(current_date, equipment.ball_mill_queue_day_end_time)
    if local < day_start_at:
        return day_start_at
    if local >= day_end_at:
        return build_aware_datetime(current_date + timedelta(days=1), equipment.ball_mill_queue_day_start_time)
    return local


BALL_MILL_OPPOSITE_POSITION_PAIRS = ((1, 4), (2, 3))
BALL_MILL_ROLLOVER_FAIL_REASON_PREFIX = "本批次容量不足，已顺延至 "
BALL_MILL_DISPATCH_RANK_FAIL_REASON_PREFIX = "__dispatch_rank__:"
BALL_MILL_DISPATCH_RANK_FAIL_REASON_SEPARATOR = "|"


def build_dispatch_rank_fail_reason(dispatch_rank, visible_reason=""):
    try:
        normalized_rank = int(dispatch_rank)
    except (TypeError, ValueError):
        normalized_rank = 0
    if normalized_rank <= 0:
        return visible_reason or ""
    return (
        f"{BALL_MILL_DISPATCH_RANK_FAIL_REASON_PREFIX}"
        f"{normalized_rank}{BALL_MILL_DISPATCH_RANK_FAIL_REASON_SEPARATOR}"
        f"{visible_reason or ''}"
    )


def extract_dispatch_rank_from_fail_reason(fail_reason):
    if (
        not isinstance(fail_reason, str)
        or not fail_reason.startswith(BALL_MILL_DISPATCH_RANK_FAIL_REASON_PREFIX)
    ):
        return None
    payload = fail_reason[len(BALL_MILL_DISPATCH_RANK_FAIL_REASON_PREFIX):]
    rank_text, _, _ = payload.partition(BALL_MILL_DISPATCH_RANK_FAIL_REASON_SEPARATOR)
    try:
        rank = int(rank_text)
    except (TypeError, ValueError):
        return None
    return rank if rank > 0 else None


def get_visible_fail_reason(fail_reason):
    if not isinstance(fail_reason, str):
        return ""
    if not fail_reason.startswith(BALL_MILL_DISPATCH_RANK_FAIL_REASON_PREFIX):
        return fail_reason
    payload = fail_reason[len(BALL_MILL_DISPATCH_RANK_FAIL_REASON_PREFIX):]
    _, separator, visible_reason = payload.partition(BALL_MILL_DISPATCH_RANK_FAIL_REASON_SEPARATOR)
    if separator:
        return visible_reason
    return ""


def select_queue_allocation_positions(allowed_positions, requested_count):
    normalized_positions = []
    for raw_position in allowed_positions:
        try:
            position_no = int(raw_position)
        except (TypeError, ValueError):
            continue
        if position_no > 0:
            normalized_positions.append(position_no)

    unique_allowed = sorted(set(normalized_positions))
    allowed_set = set(unique_allowed)

    if requested_count <= 0:
        return []

    if requested_count == 1:
        for pair in BALL_MILL_OPPOSITE_POSITION_PAIRS:
            for position_no in pair:
                if position_no in allowed_set:
                    return [position_no]
        return unique_allowed[:1]

    if requested_count == 2:
        for pair in BALL_MILL_OPPOSITE_POSITION_PAIRS:
            if pair[0] in allowed_set and pair[1] in allowed_set:
                return list(pair)
        return []

    if requested_count == 3:
        pair_orders = (
            (BALL_MILL_OPPOSITE_POSITION_PAIRS[0], BALL_MILL_OPPOSITE_POSITION_PAIRS[1]),
            (BALL_MILL_OPPOSITE_POSITION_PAIRS[1], BALL_MILL_OPPOSITE_POSITION_PAIRS[0]),
        )
        for primary_pair, secondary_pair in pair_orders:
            if primary_pair[0] in allowed_set and primary_pair[1] in allowed_set:
                for extra_position in secondary_pair:
                    if extra_position in allowed_set:
                        return sorted([primary_pair[0], primary_pair[1], extra_position])
        return []

    full_positions = [1, 2, 3, 4]
    if all(position_no in allowed_set for position_no in full_positions):
        return full_positions
    return []


def is_rolled_over_pending_request(queue_request):
    return (
        queue_request.status == BallMillQueueRequest.STATUS_PENDING
        and isinstance(queue_request.fail_reason, str)
        and queue_request.fail_reason.startswith(BALL_MILL_ROLLOVER_FAIL_REASON_PREFIX)
    )


def sort_queue_requests_for_dispatch(equipment, queue_requests):
    threshold = equipment.ball_mill_queue_heavy_user_threshold_minutes
    usage_cache = {}
    ranked_rows = []
    for req in queue_requests:
        usage = usage_cache.get(req.user_id)
        if usage is None:
            usage = get_queue_priority_usage_minutes(equipment, req.user)
            usage_cache[req.user_id] = usage
        is_heavy = usage > threshold
        rollover_priority = 0 if is_rolled_over_pending_request(req) else 1
        ranked_rows.append((1 if is_heavy else 0, rollover_priority, req.created_at, req.id, req))
    ranked_rows.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    return [item[4] for item in ranked_rows]


def build_queue_rank_snapshot(equipment):
    threshold = equipment.ball_mill_queue_heavy_user_threshold_minutes
    pending_requests = list(
        BallMillQueueRequest.objects.filter(
            equipment=equipment,
            status=BallMillQueueRequest.STATUS_PENDING,
        )
        .select_related("user")
        .order_by("created_at", "id")
    )
    ordered_pending = sort_queue_requests_for_dispatch(equipment, pending_requests)
    rank_by_request_id = {req.id: idx + 1 for idx, req in enumerate(ordered_pending)}
    usage_by_user_id = {}
    for req in pending_requests:
        if req.user_id not in usage_by_user_id:
            usage_by_user_id[req.user_id] = get_queue_priority_usage_minutes(equipment, req.user)
    return {
        "threshold_minutes": threshold,
        "pending_total": len(ordered_pending),
        "rank_by_request_id": rank_by_request_id,
        "usage_by_user_id": usage_by_user_id,
    }


def try_allocate_single_queue_request(
    queue_request,
    allocation_end_at,
    allocation_start_at=None,
    roll_over_on_failure=False,
    current_window_end_date=None,
    dispatch_rank=None,
):
    equipment = queue_request.equipment
    now = get_controlled_now()
    search_start_at = ceil_to_next_full_hour(now)
    if allocation_start_at:
        search_start_at = max(search_start_at, allocation_start_at)
    candidate_start = normalize_queue_candidate_start(equipment, search_start_at)
    duration_minutes = queue_request.actual_duration_minutes

    while candidate_start < allocation_end_at:
        candidate_end = candidate_start + timedelta(minutes=duration_minutes)
        if candidate_end > allocation_end_at:
            break
        day_end_at = build_aware_datetime(
            timezone.localtime(candidate_start).date(),
            equipment.ball_mill_queue_day_end_time,
        )
        if candidate_start >= day_end_at:
            candidate_start = normalize_queue_candidate_start(
                equipment,
                candidate_start + timedelta(hours=1),
            )
            continue

        if not month_limit_allows(equipment, queue_request.user, candidate_start, duration_minutes):
            candidate_start = normalize_queue_candidate_start(
                equipment,
                candidate_start + timedelta(hours=1),
            )
            continue

        window_state = describe_ball_mill_window(
            equipment,
            candidate_start,
            candidate_end,
            queue_request.rotation_speed_rpm,
        )
        allowed_positions = [
            p["position_no"] for p in window_state["positions"] if p.get("allowed")
        ]
        if len(allowed_positions) < queue_request.position_count:
            candidate_start = normalize_queue_candidate_start(
                equipment,
                candidate_start + timedelta(hours=1),
            )
            continue

        position_nos = select_queue_allocation_positions(
            allowed_positions,
            queue_request.position_count,
        )
        if len(position_nos) < queue_request.position_count:
            candidate_start = normalize_queue_candidate_start(
                equipment,
                candidate_start + timedelta(hours=1),
            )
            continue
        local_start = timezone.localtime(candidate_start)
        local_end = timezone.localtime(candidate_end)
        created_bookings = []
        try:
            with transaction.atomic():
                for position_no in position_nos:
                    booking = Booking(
                        equipment=equipment,
                        user=queue_request.user,
                        date=local_start.date(),
                        start_time=local_start.time().replace(second=0, microsecond=0),
                        end_time=local_end.time().replace(second=0, microsecond=0),
                        position_no=position_no,
                        operation_type=queue_request.operation_type,
                        rotation_speed_rpm=queue_request.rotation_speed_rpm,
                        milling_minutes=queue_request.milling_minutes,
                        actual_duration_minutes=duration_minutes,
                        remark=queue_request.remark or "",
                        status="active",
                        start_at=candidate_start,
                        end_at=candidate_end,
                    )
                    booking.clean()
                    booking.save()
                    created_bookings.append(booking)

                queue_request.status = BallMillQueueRequest.STATUS_ALLOCATED
                queue_request.fail_reason = build_dispatch_rank_fail_reason(dispatch_rank)
                queue_request.allocated_start_at = candidate_start
                queue_request.allocated_end_at = candidate_end
                queue_request.allocated_position_nos = position_nos
                queue_request.allocated_booking_ids = [b.id for b in created_bookings]
                queue_request.dispatched_at = get_controlled_now()
                queue_request.save(
                    update_fields=[
                        "status",
                        "fail_reason",
                        "allocated_start_at",
                        "allocated_end_at",
                        "allocated_position_nos",
                        "allocated_booking_ids",
                        "dispatched_at",
                        "updated_at",
                    ]
                )
            return True
        except Exception:
            candidate_start = normalize_queue_candidate_start(
                equipment,
                candidate_start + timedelta(hours=1),
            )

    if roll_over_on_failure and current_window_end_date:
        roll_queue_request_to_next_batch(queue_request, current_window_end_date)
        return False

    queue_request.status = BallMillQueueRequest.STATUS_REJECTED
    queue_request.fail_reason = build_dispatch_rank_fail_reason(
        dispatch_rank,
        "本次放榜窗口内未找到可用时段。",
    )
    queue_request.dispatched_at = get_controlled_now()
    queue_request.save(update_fields=["status", "fail_reason", "dispatched_at", "updated_at"])
    return False


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.all().order_by("name")
    serializer_class = EquipmentSerializer

    def get_queryset(self):
        queryset = super().get_queryset().select_related("xrd_remote_machine").prefetch_related("booking_allowed_users")
        if IsSystemAdmin().has_permission(self.request, self):
            return queryset
        if self.action == "list":
            return queryset.filter(
                is_active=True,
            ).filter(
                Q(booking_allowed_users__isnull=True) | Q(booking_allowed_users=self.request.user)
            ).distinct()
        return queryset

    def get_permissions(self):
        # 管理员操作：新建 / 修改 / 删除 / 早鸟候选列表
        admin_actions = [
            "create",
            "update",
            "partial_update",
            "destroy",
            "early_bird_candidates",
            "dispatch_queue",
            "test_clock",
            "clear_all_ball_mill_data",
            "set_electrochemical_channel_status",
            "xrd_tutorial",
            "export_usage_records",
        ]
        if self.action == "xrd_tutor_stats":
            return [IsAuthenticated(), IsSystemAdminOrTutor()]
        if self.action in admin_actions:
            return [IsAuthenticated(), IsSystemAdmin()]
        # 其它接口（available / book 等）普通登录用户即可
        return [IsAuthenticated()]

    @action(detail=False, methods=["get", "post", "delete"], url_path="test-clock")
    def test_clock(self, request):
        if request.method.lower() == "get":
            mocked = get_test_now()
            now = get_controlled_now()
            return Response(
                {
                    "mock_enabled": bool(mocked),
                    "mock_datetime": mocked.isoformat() if mocked else None,
                    "effective_now": now.isoformat(),
                    "effective_today": now.date().strftime("%Y-%m-%d"),
                }
            )

        if request.method.lower() == "delete":
            clear_test_now()
            now = get_controlled_now()
            return Response(
                {
                    "mock_enabled": False,
                    "mock_datetime": None,
                    "effective_now": now.isoformat(),
                    "effective_today": now.date().strftime("%Y-%m-%d"),
                }
            )

        parsed = parse_test_datetime_or_none(request.data.get("datetime"))
        if parsed is None:
            return Response(
                {"detail": "请提供有效的 datetime，格式示例：2026-04-12 10:30:00。"},
                status=400,
            )

        applied = set_test_now(parsed)
        return Response(
            {
                "mock_enabled": True,
                "mock_datetime": applied.isoformat(),
                "effective_now": applied.isoformat(),
                "effective_today": applied.date().strftime("%Y-%m-%d"),
            }
        )

    # GET /api/equipment/equipments/<id>/available/?date=YYYY-MM-DD
    @action(detail=True, methods=["get"], url_path="available")
    def available(self, request, pk=None):
        """
        返回某一天的所有时间片，并标记是否被占用。
        已占用时段中带出预约人姓名 booked_by，供前端显示“张三已预约”。

        返回的 equipment 字段，包含 effective_max_advance_days，
        会根据当前登录用户是否为“早鸟用户”动态计算可提前预约天数。
        """
        equipment = self.get_object()
        if not equipment.allows_booking_for_user(request.user):
            return Response({"detail": booking_user_scope_error_message()}, status=403)
        date_str = request.query_params.get("date")
        the_date = parse_date_or_today(date_str)

        unit = equipment.time_unit_minutes
        start = datetime.combine(the_date, equipment.open_time_start)
        end = datetime.combine(the_date, equipment.open_time_end)

        if equipment.is_planetary_ball_mill():
            milling_minutes = request.query_params.get("milling_minutes")
            rotation_speed_rpm = request.query_params.get("rotation_speed_rpm")
            my_recent_30d_usage_window_start, my_recent_30d_usage_window_end = (
                get_queue_priority_usage_window(equipment)
            )
            my_recent_30d_usage_minutes = clip_user_usage_minutes_in_range(
                equipment,
                request.user,
                my_recent_30d_usage_window_start,
                my_recent_30d_usage_window_end,
            )
            try:
                requested_milling_minutes = int(milling_minutes)
            except (TypeError, ValueError):
                requested_milling_minutes = None

            try:
                requested_speed_rpm = int(rotation_speed_rpm)
            except (TypeError, ValueError):
                requested_speed_rpm = None
            if requested_speed_rpm is not None:
                try:
                    equipment.validate_ball_mill_rotation_speed_rpm(requested_speed_rpm)
                except DjangoValidationError as exc:
                    return Response({"detail": exc.messages[0]}, status=400)

            if requested_milling_minutes is not None:
                if requested_milling_minutes <= 0:
                    return Response({"detail": "球磨时间必须大于 0。"}, status=400)
                if requested_milling_minutes > equipment.get_ball_mill_max_milling_minutes():
                    return Response(
                        {
                            "detail": (
                                f"球磨时间不能超过 {equipment.get_ball_mill_max_milling_minutes()} 分钟。"
                            )
                        },
                        status=400,
                    )

            equip_data = EquipmentSerializer(
                equipment,
                context={"request": request},
            ).data
            queue_snapshot = (
                build_queue_rank_snapshot(equipment)
                if equipment.ball_mill_queue_enabled
                else None
            )
            queue_overview = {
                "queue_pending_count": 0,
                "my_queue_pending_count": 0,
                "my_queue_best_rank": None,
            }
            if equipment.ball_mill_queue_enabled:
                rank_by_request_id = (queue_snapshot or {}).get("rank_by_request_id", {})
                my_pending_request_ids = list(
                    BallMillQueueRequest.objects.filter(
                        equipment=equipment,
                        status=BallMillQueueRequest.STATUS_PENDING,
                        user=request.user,
                    ).values_list("id", flat=True)
                )
                my_ranks = [
                    rank_by_request_id[request_id]
                    for request_id in my_pending_request_ids
                    if request_id in rank_by_request_id
                ]
                queue_overview = {
                    "queue_pending_count": (queue_snapshot or {}).get("pending_total", 0),
                    "my_queue_pending_count": len(my_pending_request_ids),
                    "my_queue_best_rank": min(my_ranks) if my_ranks else None,
                }

            hour_windows = (
                build_ball_mill_hour_windows(
                    equipment,
                    the_date,
                    requested_milling_minutes,
                    requested_speed_rpm,
                )
                if requested_milling_minutes
                else []
            )
            if hour_windows:
                for window in hour_windows:
                    window["queue_pending_count"] = queue_overview["queue_pending_count"]
                    window["my_queue_pending_count"] = queue_overview["my_queue_pending_count"]
                    window["my_queue_best_rank"] = queue_overview["my_queue_best_rank"]

            return Response(
                {
                    "equipment": equip_data,
                    "booking_mode": equipment.booking_mode,
                    "date": the_date.strftime("%Y-%m-%d"),
                    "hour_unit": 60,
                    "actual_duration_minutes": (
                        equipment.calculate_ball_mill_actual_minutes(requested_milling_minutes)
                        if requested_milling_minutes
                        else None
                    ),
                    "hour_windows": hour_windows,
                    "queue_pending_total": (queue_snapshot or {}).get("pending_total", 0),
                    "my_recent_30d_usage_minutes": my_recent_30d_usage_minutes,
                    "my_recent_30d_usage_window_end": timezone.localtime(
                        my_recent_30d_usage_window_end
                    ).isoformat(),
                }
            )


        if equipment.is_electrochemical_workstation():
            unit = equipment.time_unit_minutes
            start = datetime.combine(the_date, dt_time(0, 0))
            end = datetime.combine(the_date, dt_time(23, 59))
            selected_channel_no = parse_channel_no_or_none(request.query_params.get("channel_no"))
            if selected_channel_no is None:
                selected_channel_no = 1
            if selected_channel_no not in range(1, equipment.get_electrochemical_channel_count() + 1):
                return Response({"detail": "请选择通道 1-8。"}, status=400)

            channels, offline_channels = build_electrochemical_channel_options(equipment)
            now = get_controlled_now()
            current_status_available = the_date == now.date()
            current_bookings_by_channel = {}
            if current_status_available:
                current_time = now.time()
                current_bookings = (
                    Booking.objects.filter(
                        equipment=equipment,
                        date=the_date,
                        status="active",
                        start_time__lte=current_time,
                        end_time__gt=current_time,
                        position_no__gte=1,
                        position_no__lte=equipment.get_electrochemical_channel_count(),
                    )
                    .select_related("user")
                    .order_by("position_no", "end_time", "id")
                )
                for booking in current_bookings:
                    channel_no = booking.position_no
                    if channel_no in current_bookings_by_channel:
                        continue
                    user = booking.user
                    current_bookings_by_channel[channel_no] = {
                        "booked_by": getattr(user, "name", None) or getattr(user, "username", ""),
                        "booking_end_time": booking.end_time.strftime("%H:%M"),
                        "is_mine": booking.user_id == request.user.id,
                    }

            for channel in channels:
                channel_no = channel.get("channel_no")
                current_booking = current_bookings_by_channel.get(channel_no)
                channel["current_status_available"] = current_status_available
                channel["current_occupied"] = bool(current_booking)
                channel["current_booked_by"] = (
                    current_booking["booked_by"] if current_booking else None
                )
                channel["current_booking_end_time"] = (
                    current_booking["booking_end_time"] if current_booking else None
                )
                channel["current_is_mine"] = current_booking["is_mine"] if current_booking else False

            existing = (
                Booking.objects.filter(
                    equipment=equipment,
                    date=the_date,
                    status="active",
                    position_no=selected_channel_no,
                )
                .select_related("user")
            )

            occupied = []
            for booking in existing:
                user = booking.user
                booked_by = getattr(user, "name", None) or getattr(user, "username", "")
                occupied.append(
                    {
                        "booking_id": booking.id,
                        "start": booking.start_time,
                        "end": booking.end_time,
                        "booking_start_time": booking.start_time.strftime("%H:%M"),
                        "booking_end_time": booking.end_time.strftime("%H:%M"),
                        "booked_by": booked_by,
                        "is_mine": booking.user_id == request.user.id,
                    }
                )

            slots = []
            cur = start
            while cur < end:
                next_cur = cur + timedelta(minutes=unit)
                slot_end_dt = next_cur if next_cur <= end else end
                if slot_end_dt <= cur:
                    break
                slot_start = cur.time()
                slot_end = slot_end_dt.time()

                is_occupied = False
                booked_by = None
                booking_id = None
                is_mine = False
                booking_start_time = None
                booking_end_time = None
                for item in occupied:
                    if slot_start < item["end"] and slot_end > item["start"]:
                        is_occupied = True
                        booked_by = item["booked_by"]
                        booking_id = item["booking_id"]
                        is_mine = item["is_mine"]
                        booking_start_time = item["booking_start_time"]
                        booking_end_time = item["booking_end_time"]
                        break

                slots.append(
                    {
                        "start": slot_start.strftime("%H:%M"),
                        "end": slot_end.strftime("%H:%M"),
                        "occupied": is_occupied,
                        "booked_by": booked_by,
                        "booking_id": booking_id,
                        "is_mine": is_mine,
                        "booking_start_time": booking_start_time,
                        "booking_end_time": booking_end_time,
                        "channel_no": selected_channel_no,
                    }
                )
                cur = next_cur

            equip_data = EquipmentSerializer(
                equipment,
                context={"request": request},
            ).data

            return Response(
                {
                    "equipment": equip_data,
                    "booking_mode": equipment.booking_mode,
                    "date": the_date.strftime("%Y-%m-%d"),
                    "time_unit": unit,
                    "open_start": start.time().strftime("%H:%M"),
                    "open_end": end.time().strftime("%H:%M"),
                    "channel_count": equipment.get_electrochemical_channel_count(),
                    "channels": channels,
                    "selected_channel_no": selected_channel_no,
                    "selected_channel_offline": selected_channel_no in offline_channels,
                    "offline_channels": sorted(offline_channels),
                    "slots": slots,
                }
            )

        # 已有预约（只取 active），并预加载 user，避免 N+1
        existing = (
            Booking.objects.filter(
                equipment=equipment,
                date=the_date,
                status="active",
            )
            .select_related("user")
        )

        # 记录占用信息
        occupied = []
        for b in existing:
            user = b.user
            booked_by = getattr(user, "name", None) or getattr(user, "username", "")
            occupied.append(
                {
                    "start": b.start_time,
                    "end": b.end_time,
                    "booked_by": booked_by,
                }
            )

        slots = []
        cur = start
        while cur + timedelta(minutes=unit) <= end:
            slot_start = cur.time()
            slot_end = (cur + timedelta(minutes=unit)).time()

            is_occupied = False
            booked_by = None
            for o in occupied:
                if slot_start < o["end"] and slot_end > o["start"]:
                    is_occupied = True
                    booked_by = o["booked_by"]
                    break

            slots.append(
                {
                    "start": slot_start.strftime("%H:%M"),
                    "end": slot_end.strftime("%H:%M"),
                    "occupied": is_occupied,
                    "booked_by": booked_by,
                }
            )
            cur += timedelta(minutes=unit)

        # ⭐ 这里把 request 传入 serializer，让 effective_max_advance_days 正确计算
        equip_data = EquipmentSerializer(
            equipment,
            context={"request": request},
        ).data

        return Response(
            {
                "equipment": equip_data,
                "date": the_date.strftime("%Y-%m-%d"),
                "time_unit": unit,
                "open_start": equipment.open_time_start.strftime("%H:%M"),
                "open_end": equipment.open_time_end.strftime("%H:%M"),
                "slots": slots,
            }
        )

    @action(
        detail=True,
        methods=["post"],
        url_path=r"electrochemical-channel/(?P<channel_no>[^/.]+)/status",
    )
    def set_electrochemical_channel_status(self, request, pk=None, channel_no=None):
        equipment = self.get_object()
        if not equipment.is_electrochemical_workstation():
            return Response({"detail": "当前仪器不是输力强电化学工作站。"}, status=400)

        channel_no_int = parse_channel_no_or_none(channel_no)
        if channel_no_int not in range(1, equipment.get_electrochemical_channel_count() + 1):
            return Response({"detail": "请选择通道 1-8。"}, status=400)

        offline_raw = request.data.get("offline", None)
        if offline_raw is None:
            return Response({"detail": "请提供 offline 字段（true/false）。"}, status=400)
        if isinstance(offline_raw, bool):
            is_offline = offline_raw
        else:
            is_offline = str(offline_raw).lower() in {"1", "true", "yes", "on"}

        offline_channels = equipment.get_electrochemical_offline_channel_set()
        if is_offline:
            offline_channels.add(channel_no_int)
        else:
            offline_channels.discard(channel_no_int)

        equipment.electrochemical_offline_channels = sorted(offline_channels)
        equipment.save(update_fields=["electrochemical_offline_channels"])
        channels, offline_channels = build_electrochemical_channel_options(equipment)

        return Response(
            {
                "channel_no": channel_no_int,
                "offline": channel_no_int in offline_channels,
                "offline_channels": sorted(offline_channels),
                "channels": channels,
            }
        )

    @action(detail=True, methods=["get"], url_path="calendar")
    def calendar(self, request, pk=None):
        equipment = self.get_object()
        the_date = parse_date_or_today(request.query_params.get("date"))
        day_start, day_end = build_day_window(the_date)

        queryset = (
            Booking.objects.filter(
                equipment=equipment,
                status="active",
                start_at__lt=day_end,
                end_at__gt=day_start,
            )
            .select_related("user", "equipment")
            .order_by("start_at", "position_no")
        )
        return Response(BookingSerializer(queryset, many=True).data)

    @action(detail=True, methods=["get"], url_path="usage-records-export")
    def export_usage_records(self, request, pk=None):
        """Export this equipment's completed, non-cancelled bookings as UTF-8 CSV."""
        equipment = self.get_object()
        now = get_controlled_now()
        today = now.date()
        current_time = now.time()

        bookings = (
            Booking.objects.filter(equipment=equipment, status="active")
            .filter(
                Q(end_at__lte=now)
                | Q(end_at__isnull=True, date__lt=today)
                | Q(end_at__isnull=True, date=today, end_time__lte=current_time)
            )
            .select_related("user")
            .order_by("start_at", "date", "start_time", "id")
        )

        def format_local_datetime(value):
            if not value:
                return ""
            local_value = timezone.localtime(value) if timezone.is_aware(value) else value
            return local_value.strftime("%Y-%m-%d %H:%M:%S")

        def safe_text(value):
            """Prevent user-controlled text from becoming a spreadsheet formula."""
            if value is None:
                return ""
            text = str(value)
            if text.startswith(("=", "+", "-", "@", "\t", "\r")):
                return f"'{text}"
            return text

        safe_equipment_name = "".join(
            "_" if char in '\\/:*?"<>|\r\n' else char
            for char in equipment.name
        ).strip(" .") or f"instrument_{equipment.id}"
        filename = (
            f"{safe_equipment_name}_使用记录_"
            f"{timezone.localtime(now).strftime('%Y%m%d')}.csv"
        )
        ascii_filename = f"equipment_{equipment.id}_usage_records.csv"
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="{ascii_filename}"; '
            f"filename*=UTF-8''{quote(filename, safe='')}"
        )
        # Excel on Windows needs a BOM to auto-detect UTF-8 Chinese text.
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(
            [
                "记录ID",
                "仪器名称",
                "仪器类型",
                "使用人",
                "学号/工号",
                "邮箱",
                "开始时间",
                "结束时间",
                "占用时长（分钟）",
                "工位/通道号",
                "操作类型",
                "转速（r/min）",
                "球磨时间（分钟）",
                "XRD测试方式",
                "XRD扫速",
                "XRD扫描范围起点",
                "XRD扫描范围终点",
                "XRD测试结束时间",
                "预约状态",
                "备注",
                "预约创建时间",
            ]
        )

        for booking in bookings:
            start_at = booking.get_effective_start_at()
            end_at = booking.get_effective_end_at()
            duration_minutes = booking.actual_duration_minutes
            if duration_minutes is None and start_at and end_at and end_at > start_at:
                duration_minutes = int((end_at - start_at).total_seconds() // 60)

            writer.writerow(
                [
                    booking.id,
                    safe_text(equipment.name),
                    safe_text(equipment.get_booking_mode_display()),
                    safe_text(get_user_display_name(booking.user)),
                    safe_text(getattr(booking.user, "username", "")),
                    safe_text(getattr(booking.user, "email", "")),
                    format_local_datetime(start_at),
                    format_local_datetime(end_at),
                    duration_minutes if duration_minutes is not None else "",
                    booking.position_no or "",
                    safe_text(booking.get_operation_type_display() if booking.operation_type else ""),
                    booking.rotation_speed_rpm or "",
                    booking.milling_minutes or "",
                    safe_text(
                        booking.get_xrd_measurement_mode_display()
                        if booking.xrd_measurement_mode
                        else ""
                    ),
                    booking.xrd_scan_speed if booking.xrd_scan_speed is not None else "",
                    booking.xrd_scan_range_start if booking.xrd_scan_range_start is not None else "",
                    booking.xrd_scan_range_end if booking.xrd_scan_range_end is not None else "",
                    format_local_datetime(booking.xrd_test_ended_at),
                    safe_text(booking.get_status_display()),
                    safe_text(booking.remark),
                    format_local_datetime(booking.created_at),
                ]
            )

        return response

    @action(detail=True, methods=["get"], url_path="xrd-tutor-stats")
    def xrd_tutor_stats(self, request, pk=None):
        equipment = self.get_object()
        if not equipment.is_xrd():
            return Response({"detail": "当前仪器不是 XRD。"}, status=400)

        month_str = request.query_params.get("month")
        queryset = (
            Booking.objects.filter(equipment=equipment, status="active")
            .select_related("user", "user__assigned_tutor")
            .order_by("user__assigned_tutor__name", "user__name", "start_at")
        )
        is_admin = IsSystemAdmin().has_permission(request, self)
        month = None
        if month_str:
            month = parse_month_or_current(month_str)
            month_start_at, month_end_at, _ = build_month_window(month)
            queryset = queryset.filter(start_at__lt=month_end_at, end_at__gt=month_start_at)

        stats_by_tutor = {}
        for booking in queryset:
            tutor = getattr(booking.user, "assigned_tutor", None)
            tutor_id = tutor.id if tutor else None
            tutor_name = get_user_display_name(tutor) if tutor else "未分配导师"
            key = tutor_id or "unassigned"
            row = stats_by_tutor.setdefault(
                key,
                {
                    "tutor_id": tutor_id,
                    "tutor_name": tutor_name,
                    "student_count": 0,
                    "booking_count": 0,
                    "total_minutes": 0,
                    "students": {},
                },
            )
            student_key = booking.user_id
            student_row = row["students"].setdefault(
                student_key,
                {
                    "student_id": booking.user_id,
                    "student_name": get_user_display_name(booking.user),
                    "booking_count": 0,
                    "total_minutes": 0,
                    "bookings": [],
                },
            )
            local_start_at = timezone.localtime(booking.start_at) if booking.start_at else None
            local_end_at = timezone.localtime(booking.end_at) if booking.end_at else None
            counted_start_at = booking.start_at
            counted_end_at = booking.end_at
            if month and counted_start_at and counted_end_at:
                counted_start_at = max(counted_start_at, month_start_at)
                counted_end_at = min(counted_end_at, month_end_at)
            minutes = 0
            if counted_start_at and counted_end_at and counted_end_at > counted_start_at:
                minutes = int((counted_end_at - counted_start_at).total_seconds() // 60)
            student_row["bookings"].append(
                {
                    "id": booking.id,
                    "date": booking.date.strftime("%Y-%m-%d") if booking.date else "",
                    "start_time": booking.start_time.strftime("%H:%M") if booking.start_time else "",
                    "end_time": booking.end_time.strftime("%H:%M") if booking.end_time else "",
                    "start_at": local_start_at.isoformat() if local_start_at else "",
                    "end_at": local_end_at.isoformat() if local_end_at else "",
                    "actual_duration_minutes": minutes,
                    "remark": booking.remark or "",
                }
            )
            row["booking_count"] += 1
            row["total_minutes"] += minutes
            student_row["booking_count"] += 1
            student_row["total_minutes"] += minutes

        rows = []
        for row in stats_by_tutor.values():
            students = sorted(row["students"].values(), key=lambda item: item["student_name"])
            row["student_count"] = len(students)
            can_view_details = bool(is_admin or row["tutor_id"] == request.user.id)
            row["can_view_details"] = can_view_details
            row["students"] = students if can_view_details else []
            rows.append(row)
        rows.sort(key=lambda item: (item["tutor_name"] == "未分配导师", item["tutor_name"]))

        return Response(
            {
                "equipment_id": equipment.id,
                "equipment_name": equipment.name,
                "month": month.strftime("%Y-%m") if month else "all",
                "rows": rows,
            }
        )

    @action(detail=True, methods=["post"], url_path="xrd-tutorial")
    def xrd_tutorial(self, request, pk=None):
        equipment = self.get_object()
        if not equipment.is_xrd():
            return Response({"detail": "当前仪器不是 XRD。"}, status=400)

        html = request.data.get("html", "")
        equipment.xrd_tutorial_html = str(html)
        equipment.save(update_fields=["xrd_tutorial_html"])
        return Response(
            {
                "equipment_id": equipment.id,
                "xrd_tutorial_html": equipment.xrd_tutorial_html,
            }
        )

    @action(detail=True, methods=["get"], url_path="month-summary")
    def month_summary(self, request, pk=None):
        equipment = self.get_object()
        month_start = parse_month_or_current(request.query_params.get("month"))
        month_start_at, month_end_at, month_end = build_month_window(month_start)
        selected_channel_no = None
        if equipment.is_electrochemical_workstation():
            selected_channel_no = parse_channel_no_or_none(request.query_params.get("channel_no"))
            if selected_channel_no is None:
                selected_channel_no = 1
            if selected_channel_no not in range(1, equipment.get_electrochemical_channel_count() + 1):
                return Response({"detail": "请选择通道 1-8。"}, status=400)

        queryset = (
            Booking.objects.filter(
                equipment=equipment,
                status="active",
                start_at__lt=month_end_at,
                end_at__gt=month_start_at,
            )
            .select_related("user", "equipment")
            .order_by("start_at", "position_no")
        )
        if selected_channel_no is not None:
            queryset = queryset.filter(position_no=selected_channel_no)

        day_map = {}
        for booking in queryset:
            local_start_date = timezone.localtime(booking.start_at).date()
            local_end_marker = booking.end_at - timedelta(seconds=1)
            local_end_date = timezone.localtime(local_end_marker).date()

            overlap_start = max(local_start_date, month_start)
            overlap_end = min(local_end_date, month_end)
            current_date = overlap_start

            while current_date <= overlap_end:
                key = current_date.strftime("%Y-%m-%d")
                if key not in day_map:
                    day_map[key] = {
                        "date": key,
                        "has_booking": True,
                        "booking_count": 0,
                        "occupied_positions": 0,
                    }
                day_map[key]["booking_count"] += 1
                if booking.position_no:
                    day_map[key]["occupied_positions"] += 1
                current_date += timedelta(days=1)

        return Response(
            {
                "equipment_id": equipment.id,
                "month": month_start.strftime("%Y-%m"),
                "channel_no": selected_channel_no,
                "days": [day_map[key] for key in sorted(day_map.keys())],
            }
        )

    # POST /api/equipment/equipments/<id>/book/
    @action(detail=True, methods=["post"], url_path="book")
    def book(self, request, pk=None):
        equipment = self.get_object()
        if not equipment.allows_booking_for_user(request.user):
            return Response({"detail": booking_user_scope_error_message()}, status=403)
        if equipment.is_planetary_ball_mill() and equipment.ball_mill_queue_enabled and not IsSystemAdmin().has_permission(request, self):
            date_str = request.data.get("date")
            start_time = parse_time_or_none(request.data.get("start_time"))
            milling_minutes = request.data.get("milling_minutes")
            start_date = None
            try:
                start_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else None
            except Exception:
                start_date = None
            try:
                milling_minutes = int(milling_minutes)
            except (TypeError, ValueError):
                milling_minutes = None

            if start_date and start_time and milling_minutes and milling_minutes > 0:
                start_at = build_aware_datetime(start_date, start_time)
                end_at = start_at + timedelta(
                    minutes=equipment.calculate_ball_mill_actual_minutes(milling_minutes)
                )
                if equipment.is_ball_mill_in_queue_block_window(start_at, end_at):
                    direct_cutoff = timezone.localtime(equipment.get_ball_mill_direct_booking_cutoff())
                    queue_start = timezone.localtime(equipment.get_ball_mill_queue_start_at())
                    return Response(
                        {
                            "detail": (
                                f"该预约位于直约窗口外（{direct_cutoff.strftime('%Y-%m-%d %H:%M')} 至 "
                                f"{queue_start.strftime('%Y-%m-%d %H:%M')}），当前不可直约，也不可提交排队申请。"
                            )
                        },
                        status=400,
                    )
                if equipment.should_ball_mill_use_queue(start_at, end_at):
                    queue_start = timezone.localtime(equipment.get_ball_mill_queue_start_at())
                    return Response(
                        {
                            "detail": (
                                f"该预约已进入排队窗口，请提交排队申请。"
                                f"当前排队窗口起点为 {queue_start.strftime('%Y-%m-%d %H:%M')}。"
                            )
                        },
                        status=400,
                    )
        ser = BookingCreateSerializer(
            data=request.data,
            context={"request": request, "equipment": equipment},
        )
        ser.is_valid(raise_exception=True)
        booking = ser.save()
        return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"], url_path="queue")
    def queue(self, request, pk=None):
        equipment = self.get_object()
        if not equipment.is_planetary_ball_mill():
            return Response({"detail": "仅行星球磨机支持排队机制。"}, status=400)

        if request.method.lower() == "post":
            if not equipment.ball_mill_queue_enabled:
                return Response({"detail": "当前仪器未启用排队机制。"}, status=400)
            if not equipment.allows_booking_for_user(request.user):
                return Response({"detail": booking_user_scope_error_message()}, status=403)
            ser = BallMillQueueRequestCreateSerializer(
                data=request.data,
                context={"request": request, "equipment": equipment},
            )
            ser.is_valid(raise_exception=True)
            queue_request = ser.save()
            queue_snapshot = build_queue_rank_snapshot(equipment)
            threshold = queue_snapshot["threshold_minutes"]
            usage_minutes = queue_snapshot["usage_by_user_id"].get(
                request.user.id,
                get_queue_priority_usage_minutes(equipment, request.user),
            )
            is_heavy = usage_minutes > threshold
            rank = queue_snapshot["rank_by_request_id"].get(queue_request.id, 1)
            payload = BallMillQueueRequestSerializer(queue_request).data
            payload["fail_reason"] = get_visible_fail_reason(payload.get("fail_reason"))
            payload["queue_rank"] = rank
            payload["queue_display_rank"] = rank
            payload["queue_pending_total"] = queue_snapshot["pending_total"]
            payload["recent_30d_usage_minutes"] = usage_minutes
            payload["is_heavy_user"] = is_heavy
            payload["heavy_threshold_minutes"] = threshold
            return Response(payload, status=status.HTTP_201_CREATED)

        date_str = request.query_params.get("date")
        include_all = request.query_params.get("all") == "1"
        queryset = BallMillQueueRequest.objects.filter(equipment=equipment).select_related("user")
        if date_str:
            the_date = parse_date_or_today(date_str)
            queryset = queryset.filter(requested_date=the_date)

        if not include_all and not IsSystemAdmin().has_permission(request, self):
            queryset = queryset.filter(user=request.user)

        queryset = queryset.order_by("created_at", "id")
        rows = BallMillQueueRequestSerializer(queryset, many=True).data
        queue_snapshot = build_queue_rank_snapshot(equipment)
        threshold = queue_snapshot["threshold_minutes"]
        rank_by_request_id = queue_snapshot["rank_by_request_id"]
        usage_by_user_id = queue_snapshot["usage_by_user_id"]
        for row in rows:
            user_id = row.get("user")
            raw_fail_reason = row.get("fail_reason")
            usage_minutes = usage_by_user_id.get(user_id, 0)
            row["recent_30d_usage_minutes"] = usage_minutes
            row["is_heavy_user"] = usage_minutes > threshold
            row["heavy_threshold_minutes"] = threshold
            row["queue_pending_total"] = queue_snapshot["pending_total"]
            row["queue_rank"] = (
                rank_by_request_id.get(row["id"])
                if row.get("status") == BallMillQueueRequest.STATUS_PENDING
                else None
            )
            row["queue_display_rank"] = row["queue_rank"] or extract_dispatch_rank_from_fail_reason(
                raw_fail_reason
            )
            row["fail_reason"] = get_visible_fail_reason(raw_fail_reason)
        return Response(rows)

    @action(detail=True, methods=["post"], url_path="dispatch-queue")
    def dispatch_queue(self, request, pk=None):
        equipment = self.get_object()
        if not equipment.is_planetary_ball_mill():
            return Response({"detail": "仅行星球磨机支持排队机制。"}, status=400)
        if not equipment.ball_mill_queue_enabled:
            return Response({"detail": "当前仪器未启用排队机制。"}, status=400)

        force_raw = request.data.get("force", None)
        force = True if force_raw is None else str(force_raw).lower() in {"1", "true", "yes"}
        preview_raw = request.data.get("preview", None)
        preview = False if preview_raw is None else str(preview_raw).lower() in {"1", "true", "yes"}

        now = get_controlled_now()
        release_time = dt_time(0, 0)

        with transaction.atomic():
            equipment = Equipment.objects.select_for_update().get(pk=equipment.pk)
            dispatch_window_start_date, dispatch_window_end_date = get_pending_dispatch_window(
                equipment,
                anchor=now,
            )
            publish_open_at = get_dispatch_publish_open_at(equipment, dispatch_window_start_date)
            publish_open_date = publish_open_at.date()
            publish_request_date_cutoff = dispatch_window_end_date

            if not preview and not force and now < publish_open_at:
                return Response(
                    {
                        "detail": (
                            f"当前批次需在 {timezone.localtime(publish_open_at).strftime('%Y-%m-%d %H:%M')} "
                            f"后放榜，可传 force=true 强制执行。"
                        ),
                        "executed": False,
                        "equipment_id": equipment.id,
                        "dispatch_window_start_date": dispatch_window_start_date.strftime("%Y-%m-%d"),
                        "dispatch_window_end_date": dispatch_window_end_date.strftime("%Y-%m-%d"),
                        "publish_open_date": publish_open_date.strftime("%Y-%m-%d"),
                        "publish_request_date_cutoff": publish_request_date_cutoff.strftime("%Y-%m-%d"),
                        "publish_time": release_time.strftime("%H:%M"),
                        "results": [],
                    },
                    status=400,
                )

            allocation_start_at = build_aware_datetime(
                dispatch_window_start_date,
                equipment.ball_mill_queue_day_start_time,
            )
            allocation_end_at = build_aware_datetime(publish_request_date_cutoff, dt_time.max)
            pending_queryset = BallMillQueueRequest.objects.filter(
                equipment=equipment,
                status=BallMillQueueRequest.STATUS_PENDING,
                requested_date__lte=dispatch_window_end_date,
            )
            pending = list(
                pending_queryset.select_related("user").order_by("created_at", "id")
            )
            if not pending:
                return Response(
                    {
                        "executed": False,
                        "preview": preview,
                        "detail": "当前无可放榜排队申请。",
                        "equipment_id": equipment.id,
                        "dispatch_window_start_date": dispatch_window_start_date.strftime("%Y-%m-%d"),
                        "dispatch_window_end_date": dispatch_window_end_date.strftime("%Y-%m-%d"),
                        "publish_open_date": publish_open_date.strftime("%Y-%m-%d"),
                        "publish_request_date_cutoff": publish_request_date_cutoff.strftime("%Y-%m-%d"),
                        "publish_time": release_time.strftime("%H:%M"),
                        "results": [],
                    }
                )

            ordered_requests = sort_queue_requests_for_dispatch(equipment, pending)
            allocated_count = 0
            rolled_over_count = 0
            skipped_count = 0
            dispatch_results = []
            for idx, queue_request in enumerate(ordered_requests, start=1):
                if not equipment.allows_booking_for_user(queue_request.user):
                    blocked_reason = "用户已不在该设备的可预约用户范围内。"
                    if preview:
                        skipped_count += 1
                        dispatch_results.append(
                            {
                                "id": queue_request.id,
                                "theoretical_rank": idx,
                                "user": queue_request.user_id,
                                "user_name": get_user_display_name(queue_request.user),
                                "position_count": queue_request.position_count,
                                "milling_minutes": queue_request.milling_minutes,
                                "rotation_speed_rpm": queue_request.rotation_speed_rpm,
                                "status": BallMillQueueRequest.STATUS_REJECTED,
                                "result_status": "rejected",
                                "fail_reason": blocked_reason,
                                "requested_date": queue_request.requested_date.strftime("%Y-%m-%d"),
                                "allocated_start_at": None,
                                "allocated_end_at": None,
                                "allocated_position_nos": [],
                            }
                        )
                        continue

                    queue_request.status = BallMillQueueRequest.STATUS_REJECTED
                    queue_request.fail_reason = build_dispatch_rank_fail_reason(idx, blocked_reason)
                    queue_request.dispatched_at = get_controlled_now()
                    queue_request.save(
                        update_fields=[
                            "status",
                            "fail_reason",
                            "dispatched_at",
                            "updated_at",
                        ]
                    )
                    skipped_count += 1
                    dispatch_results.append(
                        {
                            "id": queue_request.id,
                            "theoretical_rank": idx,
                            "user": queue_request.user_id,
                            "user_name": get_user_display_name(queue_request.user),
                            "position_count": queue_request.position_count,
                            "milling_minutes": queue_request.milling_minutes,
                            "rotation_speed_rpm": queue_request.rotation_speed_rpm,
                            "status": queue_request.status,
                            "result_status": "rejected",
                            "fail_reason": get_visible_fail_reason(queue_request.fail_reason),
                            "requested_date": queue_request.requested_date.strftime("%Y-%m-%d"),
                            "allocated_start_at": None,
                            "allocated_end_at": None,
                            "allocated_position_nos": [],
                        }
                    )
                    continue

                allocated = try_allocate_single_queue_request(
                    queue_request,
                    allocation_end_at,
                    allocation_start_at=allocation_start_at,
                    roll_over_on_failure=True,
                    current_window_end_date=dispatch_window_end_date,
                    dispatch_rank=idx,
                )
                if allocated:
                    allocated_count += 1
                    result_status = "allocated"
                elif queue_request.status == BallMillQueueRequest.STATUS_PENDING:
                    rolled_over_count += 1
                    result_status = "rolled_over"
                else:
                    skipped_count += 1
                    result_status = "rejected"

                dispatch_results.append(
                    {
                        "id": queue_request.id,
                        "theoretical_rank": idx,
                        "user": queue_request.user_id,
                        "user_name": get_user_display_name(queue_request.user),
                        "position_count": queue_request.position_count,
                        "milling_minutes": queue_request.milling_minutes,
                        "rotation_speed_rpm": queue_request.rotation_speed_rpm,
                        "status": queue_request.status,
                        "result_status": result_status,
                        "fail_reason": get_visible_fail_reason(queue_request.fail_reason),
                        "requested_date": queue_request.requested_date.strftime("%Y-%m-%d"),
                        "allocated_start_at": (
                            timezone.localtime(queue_request.allocated_start_at).isoformat()
                            if queue_request.allocated_start_at
                            else None
                        ),
                        "allocated_end_at": (
                            timezone.localtime(queue_request.allocated_end_at).isoformat()
                            if queue_request.allocated_end_at
                            else None
                        ),
                        "allocated_position_nos": queue_request.allocated_position_nos or [],
                    }
                )

            if preview:
                next_dispatch_window_start_date = dispatch_window_end_date + timedelta(days=1)
                transaction.set_rollback(True)
            else:
                next_dispatch_window_start_date = equipment.advance_ball_mill_queue_dispatch_cursor(
                    publish_request_date_cutoff
                )

        return Response(
            {
                "executed": not preview,
                "preview": preview,
                "equipment_id": equipment.id,
                "pending_count": len(ordered_requests),
                "allocated_count": allocated_count,
                "rolled_over_count": rolled_over_count,
                "skipped_count": skipped_count,
                "allocation_window_start": timezone.localtime(allocation_start_at).isoformat(),
                "allocation_window_end": timezone.localtime(allocation_end_at).isoformat(),
                "dispatch_window_start_date": dispatch_window_start_date.strftime("%Y-%m-%d"),
                "dispatch_window_end_date": dispatch_window_end_date.strftime("%Y-%m-%d"),
                "next_dispatch_window_start_date": (
                    next_dispatch_window_start_date.strftime("%Y-%m-%d")
                    if next_dispatch_window_start_date
                    else None
                ),
                "publish_open_date": publish_open_date.strftime("%Y-%m-%d"),
                "publish_request_date_cutoff": publish_request_date_cutoff.strftime("%Y-%m-%d"),
                "publish_time": release_time.strftime("%H:%M"),
                "results": dispatch_results,
            }
        )

    @action(detail=True, methods=["post"], url_path=r"queue/(?P<queue_id>[^/.]+)/cancel")
    def cancel_queue(self, request, pk=None, queue_id=None):
        equipment = self.get_object()
        try:
            queue_request = BallMillQueueRequest.objects.get(pk=queue_id, equipment=equipment)
        except BallMillQueueRequest.DoesNotExist:
            return Response({"detail": "排队申请不存在。"}, status=404)

        if queue_request.status != BallMillQueueRequest.STATUS_PENDING:
            return Response({"detail": "仅排队中的申请可取消。"}, status=400)

        if queue_request.user_id != request.user.id and not IsSystemAdmin().has_permission(request, self):
            return Response({"detail": "无权取消他人的排队申请。"}, status=403)

        queue_request.status = BallMillQueueRequest.STATUS_CANCELLED
        queue_request.fail_reason = "用户取消排队申请。"
        queue_request.save(update_fields=["status", "fail_reason", "updated_at"])
        return Response({"status": "cancelled"})

    @action(detail=True, methods=["post"], url_path=r"queue/(?P<queue_id>[^/.]+)/delete")
    def delete_queue(self, request, pk=None, queue_id=None):
        equipment = self.get_object()
        if not IsSystemAdmin().has_permission(request, self):
            return Response({"detail": "仅系统管理员可删除排队记录。"}, status=403)

        try:
            queue_request = BallMillQueueRequest.objects.get(pk=queue_id, equipment=equipment)
        except BallMillQueueRequest.DoesNotExist:
            return Response({"detail": "排队申请不存在。"}, status=404)

        queue_request.delete()
        return Response({"status": "deleted"})

    @action(detail=True, methods=["post"], url_path="clear-all")
    def clear_all_ball_mill_data(self, request, pk=None):
        equipment = self.get_object()
        if not equipment.is_planetary_ball_mill():
            return Response({"detail": "仅行星球磨机支持该操作。"}, status=400)

        with transaction.atomic():
            deleted_queue_requests, _ = BallMillQueueRequest.objects.filter(equipment=equipment).delete()
            deleted_bookings, _ = Booking.objects.filter(equipment=equipment).delete()

        return Response(
            {
                "status": "cleared",
                "deleted_queue_requests": deleted_queue_requests,
                "deleted_bookings": deleted_bookings,
            }
        )

    # GET /api/equipment/equipments/early-bird-candidates/
    @action(detail=False, methods=["get"], url_path="early-bird-candidates")
    def early_bird_candidates(self, request):
        """
        仪器管理页面使用：获取可选择为“早鸟预约用户”的候选列表。
        仅系统管理员可访问（在 get_permissions 中已经限制）。
        """
        users = User.objects.filter(is_active=True).order_by("id")
        data = []
        for u in users:
            display_name = getattr(u, "name", None) or getattr(u, "username", "") or getattr(u, "email", "")
            data.append(
                {
                    "id": u.id,
                    "name": display_name,
                }
            )
        return Response(data)


class BookingViewSet(viewsets.ModelViewSet):
    """
    普通用户：默认只看自己的预约；允许取消自己的预约
    管理员：可以查看所有、删除/取消
    """
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        """
        当前用户“我的预约”：
        只返回 status='active' 且尚未结束的预约（进行中 + 将来的预约）。
        """
        user = request.user
        now = get_controlled_now()
        today = now.date()
        current_time = now.time()

        qs = (
            Booking.objects.filter(user=user, status="active")
            .select_related("equipment", "equipment__xrd_remote_machine")
        )

        # 还未结束：直接以 end_at 判断，兼容跨天预约
        qs = qs.filter(
            Q(end_at__gt=now) |
            Q(end_at__isnull=True, date__gt=today) |
            Q(end_at__isnull=True, date=today, end_time__gt=current_time)
        ).order_by("start_at", "date", "start_time")

        serializer = BookingSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request):
        """
        当前用户历史预约记录：
        status='active' 且已经结束的预约。
        支持按 start_date / end_date 进行日期筛选。
        """
        user = request.user
        now = get_controlled_now()
        today = now.date()
        current_time = now.time()

        qs = (
            Booking.objects.filter(user=user, status="active")
            .select_related("equipment", "equipment__xrd_remote_machine")
        )

        # 已经结束：直接以 end_at 判断，兼容跨天预约
        qs = qs.filter(
            Q(end_at__lte=now) |
            Q(end_at__isnull=True, date__lt=today) |
            Q(end_at__isnull=True, date=today, end_time__lte=current_time)
        )

        # 日期筛选
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                qs = qs.filter(date__gte=start_date)
            except ValueError:
                pass

        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                qs = qs.filter(date__lte=end_date)
            except ValueError:
                pass

        qs = qs.order_by("-start_at", "-date", "-start_time")

        serializer = BookingSerializer(qs, many=True)
        return Response(serializer.data)

    def get_queryset(self):
        qs = super().get_queryset().select_related("equipment", "equipment__xrd_remote_machine", "user")
        user = self.request.user
        if IsSystemAdmin().has_permission(self.request, self):
            return qs
        return qs.filter(user=user)

    def _booking_has_started(self, booking):
        start_at = booking.start_at
        if start_at is None and booking.date and booking.start_time:
            start_at = build_aware_datetime(booking.date, booking.start_time)
        return bool(start_at and start_at <= get_controlled_now())

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        if self._booking_has_started(booking):
            return Response(
                {"detail": "已开始或已过去的预约不能删除。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """
        取消预约：仅本人或系统管理员可取消。
        取消后状态标记为 'cancelled'。
        """
        booking = self.get_object()
        user = request.user
        if booking.user != user and not IsSystemAdmin().has_permission(request, self):
            return Response({"detail": "无权取消他人的预约。"}, status=403)
        if self._booking_has_started(booking):
            return Response(
                {"detail": "已开始或已过去的预约不能取消。"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 直接数据库更新，避免历史异常预约在取消时再次触发模型 save 副作用。
        Booking.objects.filter(pk=booking.pk).update(status="cancelled")
        return Response({"status": "cancelled"})

    @action(detail=True, methods=["post"], url_path="end-early")
    def end_early(self, request, pk=None):
        """提前结束本人正在使用的输力强预约。"""
        booking = self.get_object()

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related("equipment")
                .get(pk=booking.pk)
            )

            if booking.user_id != request.user.id:
                return Response({"detail": "只能提前结束自己的预约。"}, status=403)
            if not booking.equipment.is_electrochemical_workstation():
                return Response({"detail": "仅输力强预约支持提前结束。"}, status=400)
            if booking.status != "active":
                return Response({"detail": "当前预约不能提前结束。"}, status=400)

            start_at = booking.get_effective_start_at()
            scheduled_end_at = booking.get_effective_end_at()
            ended_at = get_controlled_now().replace(microsecond=0)

            if not start_at or not scheduled_end_at:
                return Response({"detail": "预约开始时间或结束时间不完整。"}, status=400)
            if ended_at <= start_at:
                return Response({"detail": "预约尚未开始，不能提前结束。"}, status=400)
            if ended_at >= scheduled_end_at:
                return Response({"detail": "预约时段已结束，不能提前结束。"}, status=400)

            local_ended_at = timezone.localtime(ended_at)
            actual_duration_minutes = max(
                int((ended_at - start_at).total_seconds() // 60),
                0,
            )
            Booking.objects.filter(pk=booking.pk).update(
                end_at=ended_at,
                end_time=local_ended_at.time().replace(microsecond=0),
                actual_duration_minutes=actual_duration_minutes,
            )

        return Response(
            {
                "status": "ended_early",
                "booking_id": booking.id,
                "ended_at": local_ended_at.isoformat(),
                "actual_duration_minutes": actual_duration_minutes,
            }
        )

    @action(detail=True, methods=["post"], url_path="xrd-remote-connect")
    def xrd_remote_connect(self, request, pk=None):
        booking = self.get_object()
        equipment = booking.equipment

        if booking.user_id != request.user.id:
            return Response({"detail": "只能连接自己的 XRD 预约。"}, status=403)
        if booking.status != "active" or not equipment.is_xrd():
            return Response({"detail": "当前预约不能使用 XRD 远程连接。"}, status=400)

        connect_available, disabled_reason = booking.get_xrd_remote_connect_availability()
        if not connect_available:
            return Response({"detail": disabled_reason or "未在可远程连接的 XRD 预约时间内。"}, status=403)

        end_at = booking.get_effective_end_at()

        machine = equipment.xrd_remote_machine
        if not machine:
            return Response({"detail": "该 XRD 尚未配置远程主机。"}, status=400)

        from remote_access.views import (
            GUACAMOLE_URL,
            GUAC_AUTH_PROVIDER,
            find_guacamole_connection_identifier,
            get_guacamole_auth_context,
        )

        guac_session, guac_api_url, auth_token = get_guacamole_auth_context()
        if not auth_token:
            return Response({"detail": "Guacamole 认证失败，无法创建远程连接。"}, status=500)

        connection_identifier = find_guacamole_connection_identifier(
            machine,
            guac_session,
            guac_api_url,
            auth_token,
            allow_model_fallback=True,
        )
        if not connection_identifier:
            return Response({"detail": "在 Guacamole 中找不到匹配的连接。"}, status=500)

        raw_id = f"{connection_identifier}\0c\0{GUAC_AUTH_PROVIDER}"
        client_identifier = base64.b64encode(raw_id.encode("utf-8")).decode("utf-8")
        connection_url = f"{GUACAMOLE_URL}/#/client/{client_identifier}?token={auth_token}"

        return Response(
            {
                "message": "连接就绪",
                "connection_url": connection_url,
                "booking_id": booking.id,
                "valid_until": timezone.localtime(end_at).isoformat(),
                "xrd_shutdown_notice_required": booking.is_today_last_xrd_booking(),
                "machine": {
                    "id": machine.id,
                    "name": machine.name,
                    "is_active": machine.is_active,
                },
            }
        )

    @action(detail=True, methods=["post"], url_path="xrd-end-test")
    def xrd_end_test(self, request, pk=None):
        booking = self.get_object()
        equipment = booking.equipment

        if booking.user_id != request.user.id:
            return Response({"detail": "只能结束自己的 XRD 测试。"}, status=403)
        if booking.status != "active" or not equipment.is_xrd():
            return Response({"detail": "当前预约不能结束 XRD 测试。"}, status=400)
        if booking.xrd_test_ended_at:
            return Response({"detail": "该 XRD 测试已结束。"}, status=400)

        connect_available, disabled_reason = booking.get_xrd_remote_connect_availability()
        if not connect_available:
            return Response({"detail": disabled_reason or "未在可结束测试的 XRD 预约时间内。"}, status=403)

        ended_at = get_controlled_now()
        Booking.objects.filter(pk=booking.pk, xrd_test_ended_at__isnull=True).update(
            xrd_test_ended_at=ended_at
        )
        booking.xrd_test_ended_at = ended_at
        return Response(
            {
                "status": "ended",
                "booking_id": booking.id,
                "xrd_test_ended_at": timezone.localtime(ended_at).isoformat(),
            }
        )
