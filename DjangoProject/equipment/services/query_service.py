from datetime import date, datetime, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.utils import timezone

from equipment.models import Booking, Equipment, build_local_aware_datetime
from equipment.time_control import get_controlled_now, get_controlled_today


class EquipmentQueryService:
    """Read-only equipment availability and personal booking queries."""

    MAX_LIST_LIMIT = 100

    @classmethod
    def search_equipment(cls, actor, *, query="", active_only=True, limit=20):
        queryset = cls.visible_equipment(actor, active_only=active_only)
        normalized_query = (query or "").strip()
        if normalized_query:
            queryset = queryset.filter(
                Q(name__icontains=normalized_query)
                | Q(location__icontains=normalized_query)
                | Q(description__icontains=normalized_query)
            )
        queryset = queryset.order_by("name")[: cls._normalize_limit(limit)]
        return [cls._serialize_equipment(item, actor) for item in queryset]

    @classmethod
    def visible_equipment(cls, actor, *, active_only=True):
        roles = cls._require_actor(actor)
        queryset = Equipment.objects.all().prefetch_related(
            "booking_allowed_users",
            "early_bird_users",
        )
        if active_only:
            queryset = queryset.filter(is_active=True)
        if actor.is_superuser or "系统管理员" in roles:
            return queryset
        return queryset.filter(
            Q(booking_allowed_users__isnull=True)
            | Q(booking_allowed_users=actor)
        ).distinct()

    @classmethod
    def get_my_reservations(
        cls,
        actor,
        *,
        upcoming=None,
        start_date=None,
        end_date=None,
        statuses=None,
        limit=50,
    ):
        cls._require_actor(actor)
        queryset = Booking.objects.filter(user=actor).select_related("equipment")
        if statuses:
            allowed = {value for value, _ in Booking.STATUS_CHOICES}
            normalized = set(statuses)
            unknown = normalized - allowed
            if unknown:
                raise ValidationError(f"不支持的预约状态：{', '.join(sorted(unknown))}")
            queryset = queryset.filter(status__in=normalized)
        if start_date is not None:
            queryset = queryset.filter(date__gte=cls._require_date(start_date))
        if end_date is not None:
            queryset = queryset.filter(date__lte=cls._require_date(end_date))

        now = get_controlled_now()
        today = now.date()
        current_time = now.time()
        future_filter = (
            Q(end_at__gt=now)
            | Q(end_at__isnull=True, date__gt=today)
            | Q(end_at__isnull=True, date=today, end_time__gt=current_time)
        )
        if upcoming is True:
            queryset = queryset.filter(future_filter)
            ordering = ("start_at", "date", "start_time", "id")
        elif upcoming is False:
            queryset = queryset.exclude(future_filter)
            ordering = ("-start_at", "-date", "-start_time", "-id")
        else:
            ordering = ("-date", "start_time", "id")

        normalized_limit = cls._normalize_limit(limit)
        queryset = queryset.order_by(*ordering)[:normalized_limit]
        return [cls._serialize_booking(booking) for booking in queryset]

    @classmethod
    def get_available_slots(
        cls,
        actor,
        *,
        equipment_id,
        target_date,
        position_no=None,
        rotation_speed_rpm=None,
    ):
        equipment = cls._get_visible_equipment(actor, equipment_id)
        target_date = cls._require_date(target_date)
        position_no = cls._validate_position(equipment, position_no)
        if rotation_speed_rpm is not None and equipment.is_planetary_ball_mill():
            rotation_speed_rpm = equipment.validate_ball_mill_rotation_speed_rpm(
                rotation_speed_rpm
            )

        today = get_controlled_today()
        max_advance_days = equipment.get_max_advance_days_for_user(actor)
        latest_date = today + timedelta(days=max_advance_days)
        date_allowed = today <= target_date <= latest_date
        date_reason = None
        if target_date < today:
            date_reason = "past_date"
        elif target_date > latest_date:
            date_reason = "outside_booking_window"

        bookings = list(
            Booking.objects.filter(
                equipment=equipment,
                date=target_date,
                status="active",
            ).only(
                "id",
                "date",
                "start_time",
                "end_time",
                "start_at",
                "end_at",
                "position_no",
                "rotation_speed_rpm",
            )
        )

        slots = []
        cursor = datetime.combine(target_date, equipment.open_time_start)
        day_end = datetime.combine(target_date, equipment.open_time_end)
        unit = timedelta(minutes=equipment.time_unit_minutes)
        now = get_controlled_now()

        while cursor < day_end:
            slot_end_naive = min(cursor + unit, day_end)
            slot_start = timezone.make_aware(cursor, timezone.get_current_timezone())
            slot_end = timezone.make_aware(
                slot_end_naive,
                timezone.get_current_timezone(),
            )
            availability = cls._interval_availability(
                equipment,
                bookings,
                slot_start,
                slot_end,
                position_no=position_no,
                rotation_speed_rpm=rotation_speed_rpm,
            )
            if not date_allowed:
                availability.update(available=False, reason=date_reason)
            elif slot_end <= now:
                availability.update(available=False, reason="past_time")
            slots.append(
                {
                    "start": cursor.strftime("%H:%M"),
                    "end": slot_end_naive.strftime("%H:%M"),
                    **availability,
                }
            )
            cursor = slot_end_naive

        return {
            "equipment": cls._serialize_equipment(equipment, actor),
            "date": target_date.isoformat(),
            "latest_bookable_date": latest_date.isoformat(),
            "position_no": position_no,
            "slots": slots,
        }

    @classmethod
    def check_reservation_conflict(
        cls,
        actor,
        *,
        equipment_id,
        start_at,
        end_at,
        position_no=None,
        rotation_speed_rpm=None,
    ):
        equipment = cls._get_visible_equipment(actor, equipment_id)
        start_at = cls._require_datetime(start_at, "start_at")
        end_at = cls._require_datetime(end_at, "end_at")
        if start_at >= end_at:
            raise ValidationError("start_at 必须早于 end_at。")
        position_no = cls._validate_position(equipment, position_no)
        if rotation_speed_rpm is not None and equipment.is_planetary_ball_mill():
            rotation_speed_rpm = equipment.validate_ball_mill_rotation_speed_rpm(
                rotation_speed_rpm
            )

        bookings = list(
            Booking.objects.filter(
                equipment=equipment,
                status="active",
                start_at__lt=end_at,
                end_at__gt=start_at,
            ).only(
                "id",
                "date",
                "start_time",
                "end_time",
                "start_at",
                "end_at",
                "position_no",
                "rotation_speed_rpm",
            )
        )
        result = cls._interval_availability(
            equipment,
            bookings,
            start_at,
            end_at,
            position_no=position_no,
            rotation_speed_rpm=rotation_speed_rpm,
        )
        return {
            "equipment_id": equipment.id,
            "start_at": start_at.isoformat(),
            "end_at": end_at.isoformat(),
            "position_no": position_no,
            "conflict": not result["available"],
            "reason": result["reason"],
            "conflicting_booking_count": len(bookings),
            "available_positions": result.get("available_positions"),
            "locked_rotation_speed_rpm": result.get("locked_rotation_speed_rpm"),
        }

    @classmethod
    def _interval_availability(
        cls,
        equipment,
        bookings,
        start_at,
        end_at,
        *,
        position_no,
        rotation_speed_rpm,
    ):
        overlaps = []
        for booking in bookings:
            booking_start = booking.get_effective_start_at()
            booking_end = booking.get_effective_end_at()
            if booking_start and booking_end and booking_start < end_at and booking_end > start_at:
                overlaps.append(booking)

        if equipment.is_planetary_ball_mill():
            positions = set(range(1, equipment.get_ball_mill_position_count() + 1))
            occupied = {item.position_no for item in overlaps if item.position_no}
            available_positions = sorted(positions - occupied)
            speeds = {item.rotation_speed_rpm for item in overlaps if item.rotation_speed_rpm}
            locked_speed = next(iter(speeds), None) if len(speeds) == 1 else None
            speed_conflict = bool(
                rotation_speed_rpm is not None
                and (len(speeds) > 1 or (locked_speed and locked_speed != rotation_speed_rpm))
            )
            position_conflict = (
                position_no in occupied if position_no is not None else not available_positions
            )
            available = not speed_conflict and not position_conflict
            reason = None
            if speed_conflict:
                reason = "rotation_speed_conflict"
            elif position_conflict:
                reason = "position_occupied" if position_no else "no_available_position"
            return {
                "available": available,
                "reason": reason,
                "available_positions": available_positions,
                "locked_rotation_speed_rpm": locked_speed,
            }

        if equipment.is_electrochemical_workstation():
            positions = set(range(1, equipment.get_electrochemical_channel_count() + 1))
            positions -= equipment.get_electrochemical_offline_channel_set()
            occupied = {item.position_no for item in overlaps if item.position_no}
            available_positions = sorted(positions - occupied)
            position_conflict = (
                position_no not in available_positions
                if position_no is not None
                else not available_positions
            )
            return {
                "available": not position_conflict,
                "reason": (
                    "position_unavailable" if position_no is not None else "no_available_position"
                )
                if position_conflict
                else None,
                "available_positions": available_positions,
            }

        return {
            "available": not overlaps,
            "reason": "occupied" if overlaps else None,
        }

    @classmethod
    def _get_visible_equipment(cls, actor, equipment_id):
        try:
            return cls.visible_equipment(actor).get(pk=equipment_id)
        except Equipment.DoesNotExist:
            raise PermissionDenied("无权查询该仪器或仪器不存在。")

    @classmethod
    def _require_actor(cls, actor):
        if not actor or not getattr(actor, "is_authenticated", False):
            raise PermissionDenied("需要登录后才能查询仪器预约。")
        roles = set(actor.roles.values_list("name", flat=True))
        if "land设备主机" in roles:
            raise PermissionDenied("设备主机账号不能查询仪器预约。")
        return roles

    @classmethod
    def _normalize_limit(cls, limit):
        try:
            normalized = int(limit)
        except (TypeError, ValueError):
            raise ValidationError("limit 必须是整数。")
        if normalized < 1:
            raise ValidationError("limit 必须大于 0。")
        return min(normalized, cls.MAX_LIST_LIMIT)

    @staticmethod
    def _require_date(value):
        if not isinstance(value, date) or isinstance(value, datetime):
            raise ValidationError("日期参数必须是 date 对象。")
        return value

    @staticmethod
    def _require_datetime(value, field_name):
        if not isinstance(value, datetime):
            raise ValidationError(f"{field_name} 必须是 datetime 对象。")
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value

    @staticmethod
    def _validate_position(equipment, position_no):
        if position_no is None:
            return None
        try:
            position_no = int(position_no)
        except (TypeError, ValueError):
            raise ValidationError("position_no 必须是整数。")
        if equipment.is_planetary_ball_mill():
            maximum = equipment.get_ball_mill_position_count()
        elif equipment.is_electrochemical_workstation():
            maximum = equipment.get_electrochemical_channel_count()
        else:
            return None
        if position_no not in range(1, maximum + 1):
            raise ValidationError(f"position_no 必须在 1-{maximum} 之间。")
        return position_no

    @staticmethod
    def _serialize_equipment(equipment, actor):
        return {
            "id": equipment.id,
            "name": equipment.name,
            "location": equipment.location,
            "description": equipment.description,
            "booking_mode": equipment.booking_mode,
            "booking_mode_label": equipment.get_booking_mode_display(),
            "time_unit_minutes": equipment.time_unit_minutes,
            "open_time_start": equipment.open_time_start.strftime("%H:%M"),
            "open_time_end": equipment.open_time_end.strftime("%H:%M"),
            "effective_max_advance_days": equipment.get_max_advance_days_for_user(actor),
            "is_active": equipment.is_active,
        }

    @staticmethod
    def _serialize_booking(booking):
        start_at = booking.get_effective_start_at()
        end_at = booking.get_effective_end_at()
        return {
            "id": booking.id,
            "equipment_id": booking.equipment_id,
            "equipment_name": booking.equipment.name,
            "date": booking.date.isoformat(),
            "start_time": booking.start_time.strftime("%H:%M"),
            "end_time": booking.end_time.strftime("%H:%M"),
            "start_at": start_at.isoformat() if start_at else None,
            "end_at": end_at.isoformat() if end_at else None,
            "position_no": booking.position_no,
            "status": booking.status,
            "status_label": booking.get_status_display(),
        }
