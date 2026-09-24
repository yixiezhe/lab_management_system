from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers

from .models import (
    BALL_MILL_CYCLE_PAUSE_MINUTES,
    BALL_MILL_CYCLE_RUN_MINUTES,
    BALL_MILL_QUEUE_HEAVY_USER_THRESHOLD_MINUTES,
    BallMillQueueRequest,
    Booking,
    Equipment,
    build_local_aware_datetime,
)
from .time_control import get_controlled_now, get_controlled_today


BALL_MILL_WEEKLY_PUBLISH_TIME = time(0, 0)
BALL_MILL_WEEKLY_QUEUE_ALLOCATE_DAYS = 7
BALL_MILL_WEEKLY_QUEUE_PUBLISH_LEAD_DAYS = 5
BALL_MILL_WEEKLY_DIRECT_BOOKING_MAX_DAYS = 14
BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS = 18


def validate_ball_mill_date_in_window(the_date, start_date, end_date, label):
    if the_date < start_date or the_date > end_date:
        raise serializers.ValidationError(
            f"当前仅支持{label} {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}。"
        )


def validate_ball_mill_direct_booking_date(equipment, the_date, anchor=None):
    start_date, end_date = equipment.get_ball_mill_direct_booking_window(anchor=anchor)
    validate_ball_mill_date_in_window(the_date, start_date, end_date, "直接预约")


def validate_ball_mill_queue_apply_date(equipment, the_date, anchor=None):
    start_date, end_date = equipment.get_ball_mill_queue_apply_window(anchor=anchor)
    validate_ball_mill_date_in_window(the_date, start_date, end_date, "排队申请")


def validate_ball_mill_rotation_speed(equipment, rotation_speed_rpm):
    try:
        return equipment.validate_ball_mill_rotation_speed_rpm(rotation_speed_rpm)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(exc.messages)


# Equipment Serializer
class EquipmentSerializer(serializers.ModelSerializer):
    # 当前登录用户在此仪器上的“实际可提前预约天数”（只读）
    effective_max_advance_days = serializers.SerializerMethodField()
    ball_mill_position_count = serializers.SerializerMethodField()
    ball_mill_max_milling_minutes = serializers.SerializerMethodField()
    ball_mill_cycle_run_minutes = serializers.SerializerMethodField()
    ball_mill_cycle_pause_minutes = serializers.SerializerMethodField()
    electrochemical_channel_count = serializers.SerializerMethodField()
    xrd_remote_machine_name = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = [
            "id",
            "name",
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
            "xrd_remote_machine",
            "xrd_remote_machine_name",
            "xrd_tutorial_html",
            "early_bird_max_advance_days",   # ⭐ 早鸟可提前预约天数
            "early_bird_users",              # ⭐ 早鸟用户（用户 ID 列表）
            "booking_allowed_users",
            "is_active",
            "effective_max_advance_days",    # ⭐ 对当前用户真正生效的提前天数
            "ball_mill_position_count",
            "ball_mill_max_milling_minutes",
            "ball_mill_cycle_run_minutes",
            "ball_mill_cycle_pause_minutes",
            "electrochemical_channel_count",
        ]

    def get_effective_max_advance_days(self, obj: Equipment):
        """
        根据当前请求的 user 返回“真正生效”的可提前预约天数：
        - 如果 user 是早鸟用户 → 使用 early_bird_max_advance_days
        - 否则使用 max_advance_days
        """
        request = self.context.get("request")
        user = getattr(request, "user", None)
        return obj.get_max_advance_days_for_user(user)

    def get_ball_mill_position_count(self, obj: Equipment):
        return obj.get_ball_mill_position_count()

    def get_ball_mill_max_milling_minutes(self, obj: Equipment):
        return obj.get_ball_mill_max_milling_minutes()

    def get_ball_mill_cycle_run_minutes(self, obj: Equipment):
        return BALL_MILL_CYCLE_RUN_MINUTES

    def get_ball_mill_cycle_pause_minutes(self, obj: Equipment):
        return BALL_MILL_CYCLE_PAUSE_MINUTES

    def get_electrochemical_channel_count(self, obj: Equipment):
        return obj.get_electrochemical_channel_count()

    def get_xrd_remote_machine_name(self, obj: Equipment):
        machine = getattr(obj, "xrd_remote_machine", None)
        return getattr(machine, "name", "") if machine else ""

    def validate(self, attrs):
        booking_mode = attrs.get("booking_mode", getattr(self.instance, "booking_mode", Equipment.BOOKING_MODE_STANDARD))
        time_unit_minutes = attrs.get(
            "time_unit_minutes",
            getattr(self.instance, "time_unit_minutes", 60),
        )
        if time_unit_minutes <= 0:
            raise serializers.ValidationError("时间粒度必须大于 0。")
        if booking_mode == Equipment.BOOKING_MODE_PLANETARY_BALL_MILL:
            if attrs.get("ball_mill_duration_unit_minutes", getattr(self.instance, "ball_mill_duration_unit_minutes", 12)) <= 0:
                raise serializers.ValidationError("球磨时间粒度必须大于 0。")
            min_rotation_speed = attrs.get(
                "ball_mill_min_rotation_speed_rpm",
                getattr(self.instance, "ball_mill_min_rotation_speed_rpm", 1),
            )
            max_rotation_speed = attrs.get(
                "ball_mill_max_rotation_speed_rpm",
                getattr(self.instance, "ball_mill_max_rotation_speed_rpm", None),
            )
            if min_rotation_speed <= 0:
                raise serializers.ValidationError("最小转速必须大于 0。")
            if max_rotation_speed is not None and max_rotation_speed < min_rotation_speed:
                raise serializers.ValidationError("最大转速不能小于最小转速。")
            max_actual = attrs.get(
                "ball_mill_max_actual_minutes",
                getattr(self.instance, "ball_mill_max_actual_minutes", 48 * 60),
            )
            monthly_max = attrs.get(
                "ball_mill_monthly_max_actual_minutes",
                getattr(self.instance, "ball_mill_monthly_max_actual_minutes", None),
            )
            if max_actual <= 0:
                raise serializers.ValidationError("单次最大真实预约时长必须大于 0。")
            if monthly_max is not None and monthly_max < max_actual:
                raise serializers.ValidationError("每月最大真实预约时长不能小于单次最大真实预约时长。")
            queue_start = attrs.get(
                "ball_mill_queue_day_start_time",
                getattr(self.instance, "ball_mill_queue_day_start_time", time(7, 0)),
            )
            queue_end = attrs.get(
                "ball_mill_queue_day_end_time",
                getattr(self.instance, "ball_mill_queue_day_end_time", time(22, 0)),
            )
            if queue_start >= queue_end:
                raise serializers.ValidationError("排队可分配开始时段起点必须早于终点。")
            queue_request_days = attrs.get(
                "ball_mill_queue_request_window_days",
                getattr(self.instance, "ball_mill_queue_request_window_days", 14),
            )
            queue_allocate_days = attrs.get(
                "ball_mill_queue_allocate_window_days",
                getattr(self.instance, "ball_mill_queue_allocate_window_days", 10),
            )
            queue_publish_lead_days = attrs.get(
                "ball_mill_queue_publish_lead_days",
                getattr(self.instance, "ball_mill_queue_publish_lead_days", 5),
            )
            if queue_request_days <= 0 or queue_allocate_days <= 0:
                raise serializers.ValidationError("排队提交天数和放榜分配天数都必须大于 0。")
            if queue_publish_lead_days < 0:
                raise serializers.ValidationError("放榜提前天数不能小于 0。")
            threshold = attrs.get(
                "ball_mill_queue_heavy_user_threshold_minutes",
                getattr(self.instance, "ball_mill_queue_heavy_user_threshold_minutes", BALL_MILL_QUEUE_HEAVY_USER_THRESHOLD_MINUTES),
            )
            if threshold <= 0:
                raise serializers.ValidationError("重度用户阈值必须大于 0。")
            direct_window_days = attrs.get(
                "ball_mill_direct_booking_window_days",
                getattr(self.instance, "ball_mill_direct_booking_window_days", 7),
            )
            if direct_window_days <= 0:
                raise serializers.ValidationError("直约窗口天数必须大于 0。")
        return attrs

    def _apply_ball_mill_defaults(self, validated_data):
        booking_mode = validated_data.get("booking_mode", getattr(self.instance, "booking_mode", Equipment.BOOKING_MODE_STANDARD))
        if booking_mode == Equipment.BOOKING_MODE_PLANETARY_BALL_MILL:
            validated_data["time_unit_minutes"] = 60
            validated_data["open_time_start"] = time(0, 0)
            validated_data["open_time_end"] = time(23, 59)
            validated_data["ball_mill_queue_publish_time"] = BALL_MILL_WEEKLY_PUBLISH_TIME
            validated_data["ball_mill_queue_allocate_window_days"] = BALL_MILL_WEEKLY_QUEUE_ALLOCATE_DAYS
            validated_data["ball_mill_queue_publish_lead_days"] = BALL_MILL_WEEKLY_QUEUE_PUBLISH_LEAD_DAYS
            validated_data["ball_mill_direct_booking_window_days"] = BALL_MILL_WEEKLY_DIRECT_BOOKING_MAX_DAYS
            validated_data["ball_mill_direct_booking_cutoff_time"] = BALL_MILL_WEEKLY_PUBLISH_TIME
            validated_data["max_advance_days"] = BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS
            validated_data["ball_mill_queue_request_window_days"] = BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS

            if any(
                key in validated_data for key in (
                    "ball_mill_direct_booking_window_days",
                    "ball_mill_queue_publish_lead_days",
                    "ball_mill_queue_allocate_window_days",
                    "ball_mill_queue_enabled",
                )
            ) and "ball_mill_queue_dispatch_cursor_date" not in validated_data:
                validated_data["ball_mill_queue_dispatch_cursor_date"] = None
        elif booking_mode == Equipment.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION:
            validated_data["open_time_start"] = time(0, 0)
            validated_data["open_time_end"] = time(23, 59)
            validated_data["max_advance_days"] = 7
        return validated_data

    def create(self, validated_data):
        validated_data = self._apply_ball_mill_defaults(validated_data)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._apply_ball_mill_defaults(validated_data)
        return super().update(instance, validated_data)


# Booking Serializer
class BookingSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source="equipment.name", read_only=True)
    user_name = serializers.CharField(source="user.name", read_only=True)
    end_date = serializers.SerializerMethodField()
    actual_duration_minutes = serializers.SerializerMethodField()
    xrd_test_ended = serializers.SerializerMethodField()
    xrd_remote_connect_available = serializers.SerializerMethodField()
    xrd_remote_connect_disabled_reason = serializers.SerializerMethodField()
    operation_type_display = serializers.CharField(source="get_operation_type_display", read_only=True)
    booking_mode = serializers.CharField(source="equipment.booking_mode", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "equipment",
            "equipment_name",
            "user",
            "user_name",
            "date",
            "end_date",
            "start_time",
            "end_time",
            "start_at",
            "end_at",
            "booking_mode",
            "position_no",
            "operation_type",
            "operation_type_display",
            "rotation_speed_rpm",
            "milling_minutes",
            "actual_duration_minutes",
            "xrd_test_ended_at",
            "xrd_test_ended",
            "xrd_remote_connect_available",
            "xrd_remote_connect_disabled_reason",
            "status",
            "remark",
            "created_at",
        ]
        read_only_fields = [
            "user",
            "status",
            "xrd_test_ended_at",
            "xrd_test_ended",
            "xrd_remote_connect_available",
            "xrd_remote_connect_disabled_reason",
            "created_at",
        ]

    def get_end_date(self, obj: Booking):
        if obj.end_at:
            return timezone.localtime(obj.end_at).date()
        return obj.date

    def get_actual_duration_minutes(self, obj: Booking):
        if obj.equipment and obj.equipment.is_xrd() and obj.start_at and obj.end_at:
            return max(int((obj.end_at - obj.start_at).total_seconds() // 60), 0)
        return obj.actual_duration_minutes

    def _get_xrd_remote_connect_availability(self, obj: Booking):
        cached = getattr(obj, "_xrd_remote_connect_availability", None)
        if cached is None:
            cached = obj.get_xrd_remote_connect_availability()
            obj._xrd_remote_connect_availability = cached
        return cached

    def get_xrd_test_ended(self, obj: Booking):
        return bool(obj.xrd_test_ended_at)

    def get_xrd_remote_connect_available(self, obj: Booking):
        available, _reason = self._get_xrd_remote_connect_availability(obj)
        return available

    def get_xrd_remote_connect_disabled_reason(self, obj: Booking):
        available, reason = self._get_xrd_remote_connect_availability(obj)
        return "" if available else reason


# Booking Create Serializer
class BookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = [
            "date",
            "start_time",
            "end_time",
            "remark",
            "position_no",
            "operation_type",
            "rotation_speed_rpm",
            "milling_minutes",
            "actual_duration_minutes",
        ]
        extra_kwargs = {
            "end_time": {
                "required": False,
                "allow_null": True,
            },
        }

    def validate(self, attrs):
        equipment: Equipment = self.context["equipment"]
        request = self.context["request"]
        user = request.user

        the_date = attrs.get("date")
        start = attrs.get("start_time")
        end = attrs.get("end_time")
        position_no = attrs.get("position_no")
        operation_type = attrs.get("operation_type")
        rotation_speed_rpm = attrs.get("rotation_speed_rpm")
        milling_minutes = attrs.get("milling_minutes")

        if not all([the_date, start]):
            raise serializers.ValidationError("日期与开始时间不能为空。")

        if not equipment.allows_booking_for_user(user):
            raise serializers.ValidationError("你不在该设备的可预约用户范围内。")

        # 今天日期
        today = get_controlled_today()

        # 不能预约今天之前的日期
        if the_date < today:
            raise serializers.ValidationError("日期不能小于今天。")

        # 只有已经结束的时段不可预约；当前所处时段仍可预约。
        now = get_controlled_now()

        # ⭐ 可提前预约天数（根据是否早鸟用户动态决定）
        max_days = equipment.get_max_advance_days_for_user(user)
        if the_date > today + timedelta(days=max_days):
            raise serializers.ValidationError(
                f"只能在未来 {max_days} 天内预约该仪器。"
            )

        # 粒度校验
        def to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute

        unit = equipment.time_unit_minutes
        open_time_start = time(0, 0) if equipment.is_electrochemical_workstation() else equipment.open_time_start
        open_time_end = time(23, 59) if equipment.is_electrochemical_workstation() else equipment.open_time_end
        if to_minutes(start) % unit != 0:
            raise serializers.ValidationError(f"开始时间需按 {unit} 分钟粒度对齐。")

        if start < open_time_start or start >= open_time_end:
            raise serializers.ValidationError(
                f"开始时间需在开放时段："
                f"{open_time_start.strftime('%H:%M')} - "
                f"{open_time_end.strftime('%H:%M')} 内。"
            )

        start_at = build_local_aware_datetime(the_date, start)

        if equipment.is_xrd():
            if end is None:
                raise serializers.ValidationError("请选择预约占用结束时段。")
            if to_minutes(end) % unit != 0 and end != open_time_end:
                raise serializers.ValidationError(f"结束时间需按 {unit} 分钟粒度对齐。")
            if end <= start:
                raise serializers.ValidationError("预约占用结束时间必须晚于开始时间。")
            if end > open_time_end:
                raise serializers.ValidationError(
                    f"预约占用时段需在开放时段："
                    f"{open_time_start.strftime('%H:%M')} - "
                    f"{open_time_end.strftime('%H:%M')} 内。"
                )

            end_at = build_local_aware_datetime(the_date, end)
            if the_date == today and end_at <= now:
                raise serializers.ValidationError("当前时间之前的时间段不能预约。")
            actual_duration_minutes = int((end_at - start_at).total_seconds() // 60)
            attrs["end_time"] = end.replace(second=0, microsecond=0)
            attrs["start_at"] = start_at
            attrs["end_at"] = end_at
            attrs["actual_duration_minutes"] = actual_duration_minutes
            attrs["xrd_measurement_mode"] = ""
            attrs["xrd_scan_speed"] = None
            attrs["xrd_scan_range_start"] = None
            attrs["xrd_scan_range_end"] = None
        elif equipment.is_planetary_ball_mill():
            validate_ball_mill_direct_booking_date(equipment, the_date, anchor=now)
            if start.minute != 0 or start.second != 0:
                raise serializers.ValidationError("行星球磨机仅支持整点开始预约。")
            if position_no not in range(1, equipment.get_ball_mill_position_count() + 1):
                raise serializers.ValidationError("请选择 1-4 号位。")
            if operation_type not in {Booking.OPERATION_TYPE_GRINDING, Booking.OPERATION_TYPE_CLEANING}:
                raise serializers.ValidationError("请选择球磨用途。")
            validate_ball_mill_rotation_speed(equipment, rotation_speed_rpm)
            if not milling_minutes or milling_minutes <= 0:
                raise serializers.ValidationError("球磨时间必须大于 0。")

            actual_duration_minutes = equipment.calculate_ball_mill_actual_minutes(milling_minutes)
            if actual_duration_minutes > equipment.ball_mill_max_actual_minutes:
                raise serializers.ValidationError(
                    f"真实预约时长不能超过 {equipment.ball_mill_max_actual_minutes} 分钟，"
                    f"对应球磨时间最多 {equipment.get_ball_mill_max_milling_minutes()} 分钟。"
                )

            monthly_limit = equipment.ball_mill_monthly_max_actual_minutes
            if monthly_limit:
                month_start = the_date.replace(day=1)
                if month_start.month == 12:
                    next_month_start = month_start.replace(year=month_start.year + 1, month=1, day=1)
                else:
                    next_month_start = month_start.replace(month=month_start.month + 1, day=1)
                month_start_at = build_local_aware_datetime(month_start, datetime.min.time())
                next_month_start_at = build_local_aware_datetime(next_month_start, datetime.min.time())

                monthly_bookings = Booking.objects.filter(
                    equipment=equipment,
                    user=user,
                    status="active",
                    start_at__lt=next_month_start_at,
                    end_at__gt=month_start_at,
                )
                used_minutes = 0
                for existing in monthly_bookings:
                    overlap_start = max(existing.start_at, month_start_at)
                    overlap_end = min(existing.end_at, next_month_start_at)
                    if overlap_end > overlap_start:
                        used_minutes += int((overlap_end - overlap_start).total_seconds() // 60)

                if used_minutes + actual_duration_minutes > monthly_limit:
                    raise serializers.ValidationError(
                        f"本月累计预约时长上限为 {monthly_limit} 分钟，"
                        f"当前已预约 {used_minutes} 分钟，"
                        f"本次最多还能预约 {max(monthly_limit - used_minutes, 0)} 分钟。"
                    )

            end_at = start_at + timedelta(minutes=actual_duration_minutes)
            next_booking_on_position = (
                Booking.objects.filter(
                    equipment=equipment,
                    status="active",
                    position_no=position_no,
                    start_at__gt=start_at,
                )
                .order_by("start_at")
                .first()
            )
            if next_booking_on_position and end_at > next_booking_on_position.start_at:
                allowed_actual_minutes = max(
                    int((next_booking_on_position.start_at - start_at).total_seconds() // 60),
                    0,
                )
                allowed_milling_minutes = equipment.calculate_ball_mill_max_milling_minutes(
                    allowed_actual_minutes
                )
                conflict_start_text = timezone.localtime(next_booking_on_position.start_at).strftime(
                    "%Y-%m-%d %H:%M"
                )
                raise serializers.ValidationError(
                    f"{position_no} 号位在 {conflict_start_text} 已有预约，"
                    f"当前开始时间下最多可输入球磨 {allowed_milling_minutes} 分钟"
                    f"（真实 {allowed_actual_minutes} 分钟）。"
                )

            local_end_at = timezone.localtime(end_at)
            attrs["end_time"] = local_end_at.time().replace(second=0, microsecond=0)
            attrs["start_at"] = start_at
            attrs["end_at"] = end_at
            attrs["actual_duration_minutes"] = actual_duration_minutes
        else:
            if end is None:
                raise serializers.ValidationError("结束时间不能为空。")
            if start >= end:
                raise serializers.ValidationError("开始时间必须早于结束时间。")
            is_terminal_electrochemical_end = (
                equipment.is_electrochemical_workstation()
                and end == open_time_end
            )
            if to_minutes(end) % unit != 0 and not is_terminal_electrochemical_end:
                raise serializers.ValidationError(f"结束时间需按 {unit} 分钟粒度对齐。")
            if end > open_time_end:
                raise serializers.ValidationError(
                    f"结束时间需在开放时段："
                    f"{open_time_start.strftime('%H:%M')} - "
                    f"{open_time_end.strftime('%H:%M')} 内。"
                )
            if equipment.is_electrochemical_workstation():
                if position_no not in range(1, equipment.get_electrochemical_channel_count() + 1):
                    raise serializers.ValidationError("请选择通道 1-8。")
                if position_no in equipment.get_electrochemical_offline_channel_set():
                    raise serializers.ValidationError(f"通道 {position_no} 当前已暂时下线。")
            end_at = build_local_aware_datetime(the_date, end)
            attrs["start_at"] = start_at
            attrs["end_at"] = end_at
            attrs["actual_duration_minutes"] = to_minutes(end) - to_minutes(start)

        if attrs["end_at"] <= now:
            raise serializers.ValidationError("当前时间之前的时间段不能预约。")

        booking = Booking(
            equipment=equipment,
            user=user,
            date=the_date,
            start_time=start,
            end_time=attrs["end_time"],
            status="active",
            remark=attrs.get("remark", ""),
            position_no=position_no,
            operation_type=operation_type or "",
            rotation_speed_rpm=rotation_speed_rpm,
            milling_minutes=milling_minutes,
            actual_duration_minutes=attrs.get("actual_duration_minutes"),
            xrd_measurement_mode=attrs.get("xrd_measurement_mode", ""),
            xrd_scan_speed=attrs.get("xrd_scan_speed"),
            xrd_scan_range_start=attrs.get("xrd_scan_range_start"),
            xrd_scan_range_end=attrs.get("xrd_scan_range_end"),
            start_at=attrs["start_at"],
            end_at=attrs["end_at"],
        )
        booking.clean()

        return attrs

    def create(self, validated_data):
        equipment: Equipment = self.context["equipment"]
        user = self.context["request"].user
        return Booking.objects.create(
            equipment=equipment,
            user=user,
            **validated_data,
            status="active",
        )


class BallMillQueueRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    operation_type_display = serializers.CharField(source="get_operation_type_display", read_only=True)

    class Meta:
        model = BallMillQueueRequest
        fields = [
            "id",
            "equipment",
            "user",
            "user_name",
            "requested_date",
            "requested_start_time",
            "position_count",
            "operation_type",
            "operation_type_display",
            "rotation_speed_rpm",
            "milling_minutes",
            "actual_duration_minutes",
            "remark",
            "status",
            "fail_reason",
            "allocated_start_at",
            "allocated_end_at",
            "allocated_position_nos",
            "allocated_booking_ids",
            "dispatched_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "actual_duration_minutes",
            "status",
            "fail_reason",
            "allocated_start_at",
            "allocated_end_at",
            "allocated_position_nos",
            "allocated_booking_ids",
            "dispatched_at",
            "created_at",
            "updated_at",
        ]


class BallMillQueueRequestCreateSerializer(serializers.ModelSerializer):
    target_date = serializers.DateField(write_only=True)

    class Meta:
        model = BallMillQueueRequest
        fields = [
            "target_date",
            "position_count",
            "operation_type",
            "rotation_speed_rpm",
            "milling_minutes",
            "remark",
        ]

    def validate(self, attrs):
        equipment: Equipment = self.context["equipment"]
        request = self.context["request"]
        user = request.user

        if not equipment.is_planetary_ball_mill():
            raise serializers.ValidationError("仅行星球磨机支持排队机制。")
        if not equipment.ball_mill_queue_enabled:
            raise serializers.ValidationError("当前仪器未启用排队机制。")
        if not equipment.allows_booking_for_user(user):
            raise serializers.ValidationError("你不在该设备的可预约用户范围内。")

        position_count = attrs.get("position_count")
        operation_type = attrs.get("operation_type")
        rotation_speed_rpm = attrs.get("rotation_speed_rpm")
        milling_minutes = attrs.get("milling_minutes")

        if not all([position_count, operation_type, rotation_speed_rpm, milling_minutes]):
            raise serializers.ValidationError("排队申请信息不完整。")

        if position_count not in range(1, equipment.get_ball_mill_position_count() + 1):
            raise serializers.ValidationError("需求工位数必须为 1-4。")
        if operation_type not in {Booking.OPERATION_TYPE_GRINDING, Booking.OPERATION_TYPE_CLEANING}:
            raise serializers.ValidationError("请选择球磨用途。")
        validate_ball_mill_rotation_speed(equipment, rotation_speed_rpm)
        if milling_minutes <= 0:
            raise serializers.ValidationError("球磨时间必须大于 0。")

        actual_duration_minutes = equipment.calculate_ball_mill_actual_minutes(milling_minutes)
        if actual_duration_minutes > equipment.ball_mill_max_actual_minutes:
            raise serializers.ValidationError(
                f"真实预约时长不能超过 {equipment.ball_mill_max_actual_minutes} 分钟，"
                f"对应球磨时间最多 {equipment.get_ball_mill_max_milling_minutes()} 分钟。"
            )
        attrs["actual_duration_minutes"] = actual_duration_minutes

        today = get_controlled_today()
        now = get_controlled_now()
        target_date = attrs.get("target_date")
        if target_date < today:
            raise serializers.ValidationError("排队申请日期不能早于今天。")
        validate_ball_mill_queue_apply_date(equipment, target_date, anchor=now)

        pending_count = BallMillQueueRequest.objects.filter(
            equipment=equipment,
            user=user,
            status=BallMillQueueRequest.STATUS_PENDING,
        ).count()
        if pending_count >= 3:
            raise serializers.ValidationError("最多只能同时保留 3 条排队中的申请。")

        attrs.pop("target_date", None)
        attrs["requested_date"] = target_date
        attrs["requested_start_time"] = equipment.ball_mill_queue_day_start_time

        threshold = equipment.ball_mill_queue_heavy_user_threshold_minutes or BALL_MILL_QUEUE_HEAVY_USER_THRESHOLD_MINUTES
        # 轻量提示：不拦截，仅由放榜排序决定优先级
        attrs["_queue_heavy_threshold_minutes"] = threshold
        return attrs

    def create(self, validated_data):
        equipment: Equipment = self.context["equipment"]
        user = self.context["request"].user
        validated_data.pop("_queue_heavy_threshold_minutes", None)
        return BallMillQueueRequest.objects.create(
            equipment=equipment,
            user=user,
            **validated_data,
            status=BallMillQueueRequest.STATUS_PENDING,
        )
