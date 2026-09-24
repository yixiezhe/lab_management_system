from datetime import datetime, timedelta, time as dt_time
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .time_control import get_controlled_now, get_controlled_today


BALL_MILL_CYCLE_RUN_MINUTES = 12
BALL_MILL_CYCLE_PAUSE_MINUTES = 6
BALL_MILL_MAX_ACTUAL_MINUTES = 48 * 60
BALL_MILL_POSITION_COUNT = 4
BALL_MILL_QUEUE_HEAVY_USER_THRESHOLD_MINUTES = 72 * 60
BALL_MILL_DIRECT_BOOKING_WINDOW_DAYS = 7
ELECTROCHEMICAL_CHANNEL_COUNT = 8


def build_local_aware_datetime(date_value, time_value):
    naive_dt = datetime.combine(date_value, time_value)
    return timezone.make_aware(naive_dt, timezone.get_current_timezone())


class Equipment(models.Model):
    BOOKING_MODE_STANDARD = "standard"
    BOOKING_MODE_PLANETARY_BALL_MILL = "planetary_ball_mill"
    BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION = "electrochemical_workstation"
    BOOKING_MODE_XRD = "xrd"
    BOOKING_MODE_CHOICES = (
        (BOOKING_MODE_STANDARD, "普通仪器"),
        (BOOKING_MODE_PLANETARY_BALL_MILL, "行星球磨机"),
        (BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION, "输力强电化学工作站"),
        (BOOKING_MODE_XRD, "XRD"),
    )

    name = models.CharField("仪器名称", max_length=100, unique=True)
    location = models.CharField("放置地点", max_length=200, blank=True, default="")
    description = models.TextField("说明", blank=True, default="")
    booking_mode = models.CharField(
        "预约模式",
        max_length=30,
        choices=BOOKING_MODE_CHOICES,
        default=BOOKING_MODE_STANDARD,
    )

    # 时间配置
    time_unit_minutes = models.PositiveSmallIntegerField("时间粒度(分钟)", default=60)  # 时间粒度，单位为分钟
    open_time_start = models.TimeField("开放起始时间", default="08:00")
    open_time_end = models.TimeField("开放结束时间", default="22:00")
    max_advance_days = models.PositiveSmallIntegerField("可提前预约天数", default=7)
    ball_mill_duration_unit_minutes = models.PositiveSmallIntegerField(
        "球磨时间粒度(分钟)",
        default=12,
        help_text="仅行星球磨机生效，用户输入球磨时间时需按此粒度对齐。",
    )
    ball_mill_min_rotation_speed_rpm = models.PositiveIntegerField(
        "最小转速(r/min)",
        default=1,
        help_text="仅行星球磨机生效，允许预约/排队时填写的最小转速。",
    )
    ball_mill_max_rotation_speed_rpm = models.PositiveIntegerField(
        "最大转速(r/min)",
        null=True,
        blank=True,
        default=None,
        help_text="仅行星球磨机生效，允许预约/排队时填写的最大转速；为空表示不限制。",
    )
    ball_mill_max_actual_minutes = models.PositiveIntegerField(
        "单次最大真实预约时长(分钟)",
        default=BALL_MILL_MAX_ACTUAL_MINUTES,
        help_text="仅行星球磨机生效，单次预约真实时长上限。",
    )
    ball_mill_monthly_max_actual_minutes = models.PositiveIntegerField(
        "每月最大真实预约时长(分钟)",
        null=True,
        blank=True,
        default=None,
        help_text="仅行星球磨机生效，按用户统计的每月累计真实预约时长上限；为空表示不限制。",
    )
    ball_mill_queue_enabled = models.BooleanField(
        "启用排队机制",
        default=False,
        help_text="仅行星球磨机生效。启用后普通用户提交预约将进入排队，由系统统一分配。",
    )
    ball_mill_queue_publish_time = models.TimeField(
        "排队放榜时间",
        default="12:00",
        help_text="每日到达该时间后执行排队分配。",
    )
    ball_mill_queue_request_window_days = models.PositiveSmallIntegerField(
        "可提前提交排队天数",
        default=14,
        help_text="用户最多可提前多少天提交排队申请。",
    )
    ball_mill_queue_allocate_window_days = models.PositiveSmallIntegerField(
        "单次放榜分配天数",
        default=10,
        help_text="每次放榜时，最多向后分配多少天。",
    )
    ball_mill_queue_dispatch_cursor_date = models.DateField(
        "排队放榜分配游标日期",
        null=True,
        blank=True,
        default=None,
        help_text=(
            "分批放榜模式下“下一批分配窗口”的起始日期。"
            "为空时自动以当前直约窗口边界日期为起点。"
        ),
    )
    ball_mill_queue_publish_lead_days = models.PositiveSmallIntegerField(
        "放榜提前天数",
        default=5,
        help_text=(
            "仅当排队申请的期望日期距离直约窗口边界不超过该天数时，"
            "才会在当日放榜中参与分配。"
        ),
    )
    ball_mill_queue_day_start_time = models.TimeField(
        "排队可分配开始时段起点",
        default="07:00",
        help_text="排队分配的开始时间不得早于该时刻。",
    )
    ball_mill_queue_day_end_time = models.TimeField(
        "排队可分配开始时段终点",
        default="22:00",
        help_text="排队分配的开始时间必须早于该时刻。",
    )
    ball_mill_queue_heavy_user_threshold_minutes = models.PositiveIntegerField(
        "重度用户阈值(分钟/30天)",
        default=BALL_MILL_QUEUE_HEAVY_USER_THRESHOLD_MINUTES,
        help_text="滚动30天使用时长超过该阈值的用户，会被排到后层队列。",
    )
    ball_mill_direct_booking_window_days = models.PositiveSmallIntegerField(
        "直约窗口天数",
        default=BALL_MILL_DIRECT_BOOKING_WINDOW_DAYS,
        help_text="开始时间落在该窗口内可直接预约；超过窗口走排队。",
    )
    ball_mill_direct_booking_cutoff_time = models.TimeField(
        "直约窗口截止时刻",
        default="07:00",
        help_text="窗口边界时刻（如第8天 07:00 之后走排队）。",
    )
    electrochemical_offline_channels = models.JSONField(
        "电化学下线通道",
        default=list,
        blank=True,
        help_text="仅输力强电化学工作站生效；填写已暂时下线的通道号。",
    )
    xrd_remote_machine = models.ForeignKey(
        "remote_access.RdpMachine",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="xrd_equipments",
        verbose_name="XRD远程主机",
        help_text="仅 XRD 生效；用户在本人预约时段内可通过该主机远程连接。",
    )
    xrd_tutorial_html = models.TextField(
        "XRD使用教程HTML",
        blank=True,
        default="The quick brown fox jumps over the lazy dog",
        help_text="仅 XRD 生效；前端教程窗口展示的 HTML 内容。",
    )

    # ⭐ 早鸟配置
    # 早鸟用户可以拥有单独的“可提前预约天数”，优先级高于 max_advance_days
    early_bird_max_advance_days = models.PositiveSmallIntegerField(
        "早鸟可提前预约天数", default=7, help_text="仅对选中的早鸟用户生效；未选择则使用普通天数"
    )
    early_bird_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="早鸟用户",
        related_name="early_bird_equipments",
        blank=True,
        help_text="这些用户可以按早鸟天数提前预约此仪器",
    )
    booking_allowed_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="可预约用户",
        related_name="booking_allowed_equipments",
        blank=True,
        help_text="为空表示所有登录用户均可预约；设置后仅选中的用户可预约或提交排队申请。",
    )

    is_active = models.BooleanField("启用", default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "仪器"
        verbose_name_plural = verbose_name
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_planetary_ball_mill():
            self.time_unit_minutes = 60
            self.open_time_start = datetime.strptime("00:00", "%H:%M").time()
            self.open_time_end = datetime.strptime("23:59", "%H:%M").time()
            if self.ball_mill_queue_enabled and not self.ball_mill_queue_dispatch_cursor_date:
                self.ball_mill_queue_dispatch_cursor_date = self.get_ball_mill_queue_dispatch_start_date()
            if not self.ball_mill_queue_enabled:
                self.ball_mill_queue_dispatch_cursor_date = None
        if self.is_electrochemical_workstation():
            self.open_time_start = datetime.strptime("00:00", "%H:%M").time()
            self.open_time_end = datetime.strptime("23:59", "%H:%M").time()
            self.max_advance_days = 7
            self.electrochemical_offline_channels = sorted(self.get_electrochemical_offline_channel_set())
        else:
            self.electrochemical_offline_channels = []
        super().save(*args, **kwargs)

    def get_max_advance_days_for_user(self, user):
        """
        返回某个用户对该仪器真正生效的“可提前预约天数”：
        - 如果是早鸟用户 → 使用 early_bird_max_advance_days
        - 否则使用普通的 max_advance_days
        """
        if self.is_electrochemical_workstation():
            return 7
        if user and user.is_authenticated and self.early_bird_users.filter(pk=user.pk).exists():
            return self.early_bird_max_advance_days
        return self.max_advance_days

    def allows_booking_for_user(self, user):
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_system_admin", False):
            return True
        if not self.booking_allowed_users.exists():
            return True
        return self.booking_allowed_users.filter(pk=user.pk).exists()

    def is_planetary_ball_mill(self):
        return self.booking_mode == self.BOOKING_MODE_PLANETARY_BALL_MILL

    def is_electrochemical_workstation(self):
        return self.booking_mode == self.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION

    def is_xrd(self):
        return self.booking_mode == self.BOOKING_MODE_XRD

    @staticmethod
    def get_electrochemical_channel_count():
        return ELECTROCHEMICAL_CHANNEL_COUNT

    def get_electrochemical_offline_channel_set(self):
        channels = set()
        for raw in self.electrochemical_offline_channels or []:
            try:
                channel_no = int(raw)
            except (TypeError, ValueError):
                continue
            if 1 <= channel_no <= self.get_electrochemical_channel_count():
                channels.add(channel_no)
        return channels

    @staticmethod
    def calculate_ball_mill_actual_minutes(milling_minutes):
        if not milling_minutes:
            return 0
        pauses = milling_minutes // BALL_MILL_CYCLE_RUN_MINUTES
        return milling_minutes + pauses * BALL_MILL_CYCLE_PAUSE_MINUTES

    @staticmethod
    def get_ball_mill_position_count():
        return BALL_MILL_POSITION_COUNT

    @staticmethod
    def calculate_ball_mill_max_milling_minutes(max_actual_minutes):
        if not max_actual_minutes or max_actual_minutes <= 0:
            return 0
        low, high = 0, int(max_actual_minutes)
        while low < high:
            mid = (low + high + 1) // 2
            if Equipment.calculate_ball_mill_actual_minutes(mid) <= max_actual_minutes:
                low = mid
            else:
                high = mid - 1
        return low

    def get_ball_mill_max_milling_minutes(self):
        return self.calculate_ball_mill_max_milling_minutes(self.ball_mill_max_actual_minutes)

    def validate_ball_mill_rotation_speed_rpm(self, rpm):
        if rpm is None:
            raise ValidationError("请填写转速。")
        try:
            rpm_value = int(rpm)
        except (TypeError, ValueError):
            raise ValidationError("转速必须为整数。")

        if rpm_value <= 0:
            raise ValidationError("转速必须大于 0。")

        min_rpm = int(self.ball_mill_min_rotation_speed_rpm or 1)
        max_rpm = self.ball_mill_max_rotation_speed_rpm

        if rpm_value < min_rpm:
            raise ValidationError(f"转速不能低于 {min_rpm} r/min。")
        if max_rpm is not None and rpm_value > max_rpm:
            raise ValidationError(f"转速不能高于 {max_rpm} r/min。")
        return rpm_value

    def get_ball_mill_current_week_monday(self, anchor=None):
        today = get_controlled_now(anchor=anchor).date()
        return today - timedelta(days=today.weekday())

    def get_ball_mill_weekly_publish_datetime(self, anchor=None):
        week_monday = self.get_ball_mill_current_week_monday(anchor=anchor)
        publish_date = week_monday + timedelta(days=2)  # 周三 00:00
        return timezone.make_aware(
            datetime.combine(publish_date, dt_time.min),
            timezone.get_current_timezone(),
        )

    def is_ball_mill_weekly_published(self, anchor=None):
        return get_controlled_now(anchor=anchor) >= self.get_ball_mill_weekly_publish_datetime(anchor=anchor)

    def get_ball_mill_direct_booking_window(self, anchor=None):
        week_monday = self.get_ball_mill_current_week_monday(anchor=anchor)
        if self.is_ball_mill_weekly_published(anchor=anchor):
            # 放榜后：开放本周 + 下一周直接预约
            return week_monday, week_monday + timedelta(days=13)
        # 放榜前：仅开放本周直接预约
        return week_monday, week_monday + timedelta(days=6)

    def get_ball_mill_direct_booking_cutoff(self, anchor=None):
        _, direct_end_date = self.get_ball_mill_direct_booking_window(anchor=anchor)
        cutoff_date = direct_end_date + timedelta(days=1)
        return timezone.make_aware(
            datetime.combine(cutoff_date, dt_time.min),
            timezone.get_current_timezone(),
        )

    def get_ball_mill_queue_publish_request_date_cutoff(self, anchor=None):
        _, end_date = self.get_ball_mill_queue_dispatch_window(anchor=anchor)
        return end_date

    def get_ball_mill_queue_base_start_date(self, anchor=None):
        start_date, _ = self.get_ball_mill_queue_apply_window(anchor=anchor)
        return start_date

    def get_ball_mill_queue_dispatch_start_date(self, anchor=None, use_cursor=False):
        if use_cursor and self.ball_mill_queue_dispatch_cursor_date:
            return self.ball_mill_queue_dispatch_cursor_date
        week_monday = self.get_ball_mill_current_week_monday(anchor=anchor)
        if self.is_ball_mill_weekly_published(anchor=anchor):
            return week_monday + timedelta(days=14)
        return week_monday + timedelta(days=7)

    def get_ball_mill_queue_dispatch_window(self, anchor=None, use_cursor=False):
        start_date = self.get_ball_mill_queue_dispatch_start_date(anchor=anchor, use_cursor=use_cursor)
        end_date = start_date + timedelta(days=6)
        return start_date, end_date

    def get_ball_mill_queue_apply_window(self, anchor=None):
        week_monday = self.get_ball_mill_current_week_monday(anchor=anchor)
        offset_days = 14 if self.is_ball_mill_weekly_published(anchor=anchor) else 7
        start_date = week_monday + timedelta(days=offset_days)
        end_date = start_date + timedelta(days=6)
        return start_date, end_date

    def get_ball_mill_queue_publish_open_date(self, anchor=None, use_cursor=False):
        start_date = self.get_ball_mill_queue_dispatch_start_date(anchor=anchor, use_cursor=use_cursor)
        return start_date - timedelta(days=5)

    def get_ball_mill_queue_start_at(self, anchor=None):
        start_date, _ = self.get_ball_mill_queue_apply_window(anchor=anchor)
        return timezone.make_aware(
            datetime.combine(start_date, dt_time.min),
            timezone.get_current_timezone(),
        )

    def is_ball_mill_in_queue_block_window(self, start_at, end_at, anchor=None):
        if not self.ball_mill_queue_enabled:
            return False
        direct_cutoff = self.get_ball_mill_direct_booking_cutoff(anchor=anchor)
        queue_start_at = self.get_ball_mill_queue_start_at(anchor=anchor)
        if queue_start_at <= direct_cutoff:
            return False
        return start_at < queue_start_at and end_at > direct_cutoff

    def advance_ball_mill_queue_dispatch_cursor(self, current_window_end_date):
        next_start_date = current_window_end_date + timedelta(days=1)
        self.ball_mill_queue_dispatch_cursor_date = next_start_date
        self.save(update_fields=["ball_mill_queue_dispatch_cursor_date"])
        return next_start_date

    def should_ball_mill_use_queue(self, start_at, end_at, anchor=None):
        if not self.ball_mill_queue_enabled:
            return False
        queue_start_at = self.get_ball_mill_queue_start_at(anchor=anchor)
        return start_at >= queue_start_at or end_at > queue_start_at

    def clean(self):
        if self.time_unit_minutes <= 0:
            raise ValidationError("时间粒度必须大于 0。")
        if self.open_time_start >= self.open_time_end:
            raise ValidationError("开放起始时间必须早于开放结束时间。")
        if self.ball_mill_duration_unit_minutes <= 0:
            raise ValidationError("球磨时间粒度必须大于 0。")
        if self.ball_mill_min_rotation_speed_rpm <= 0:
            raise ValidationError("最小转速必须大于 0。")
        if (
            self.ball_mill_max_rotation_speed_rpm is not None
            and self.ball_mill_max_rotation_speed_rpm < self.ball_mill_min_rotation_speed_rpm
        ):
            raise ValidationError("最大转速不能小于最小转速。")
        if self.ball_mill_max_actual_minutes <= 0:
            raise ValidationError("单次最大真实预约时长必须大于 0。")
        if (
            self.ball_mill_monthly_max_actual_minutes is not None
            and self.ball_mill_monthly_max_actual_minutes < self.ball_mill_max_actual_minutes
        ):
            raise ValidationError("每月最大真实预约时长不能小于单次最大真实预约时长。")
        if self.ball_mill_queue_request_window_days <= 0:
            raise ValidationError("可提前提交排队天数必须大于 0。")
        if self.ball_mill_queue_allocate_window_days <= 0:
            raise ValidationError("单次放榜分配天数必须大于 0。")
        if self.ball_mill_queue_publish_lead_days < 0:
            raise ValidationError("放榜提前天数不能小于 0。")
        if self.ball_mill_queue_day_start_time >= self.ball_mill_queue_day_end_time:
            raise ValidationError("排队可分配开始时段起点必须早于终点。")
        if self.ball_mill_queue_heavy_user_threshold_minutes <= 0:
            raise ValidationError("重度用户阈值必须大于 0。")
        if self.ball_mill_direct_booking_window_days <= 0:
            raise ValidationError("直约窗口天数必须大于 0。")
        if self.is_electrochemical_workstation() and self.max_advance_days != 7:
            raise ValidationError("输力强电化学工作站最多可提前预约 7 天。")


class Booking(models.Model):
    STATUS_CHOICES = (
        ("active", "已预约"),
        ("cancelled", "已取消"),
    )
    OPERATION_TYPE_GRINDING = "grinding"
    OPERATION_TYPE_CLEANING = "cleaning"
    OPERATION_TYPE_CHOICES = (
        (OPERATION_TYPE_GRINDING, "磨材料"),
        (OPERATION_TYPE_CLEANING, "洗罐子"),
    )
    XRD_MEASUREMENT_MODE_INSTANT = "instant"
    XRD_MEASUREMENT_MODE_IN_SITU = "in_situ"
    XRD_MEASUREMENT_MODE_CHOICES = (
        (XRD_MEASUREMENT_MODE_INSTANT, "即时测"),
        (XRD_MEASUREMENT_MODE_IN_SITU, "原位"),
    )

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="仪器",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="equipment_bookings",
        verbose_name="预约人",
    )

    date = models.DateField("日期")
    start_time = models.TimeField("开始时间")
    end_time = models.TimeField("结束时间")
    start_at = models.DateTimeField("开始时间点", null=True, blank=True)
    end_at = models.DateTimeField("结束时间点", null=True, blank=True)
    position_no = models.PositiveSmallIntegerField("工位号", null=True, blank=True)
    operation_type = models.CharField(
        "操作类型",
        max_length=20,
        choices=OPERATION_TYPE_CHOICES,
        blank=True,
        default="",
    )
    rotation_speed_rpm = models.PositiveIntegerField("转速(r/min)", null=True, blank=True)
    milling_minutes = models.PositiveIntegerField("球磨时间(分钟)", null=True, blank=True)
    actual_duration_minutes = models.PositiveIntegerField("真实预约时长(分钟)", null=True, blank=True)
    xrd_measurement_mode = models.CharField(
        "XRD测试方式",
        max_length=20,
        choices=XRD_MEASUREMENT_MODE_CHOICES,
        blank=True,
        default="",
    )
    xrd_scan_speed = models.DecimalField("XRD扫速", max_digits=8, decimal_places=3, null=True, blank=True)
    xrd_scan_range_start = models.DecimalField("XRD扫描范围起点", max_digits=8, decimal_places=3, null=True, blank=True)
    xrd_scan_range_end = models.DecimalField("XRD扫描范围终点", max_digits=8, decimal_places=3, null=True, blank=True)
    xrd_test_ended_at = models.DateTimeField("XRD测试结束时间", null=True, blank=True)

    status = models.CharField(
        "状态", max_length=20, choices=STATUS_CHOICES, default="active"
    )
    remark = models.CharField("备注", max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "仪器预约"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["equipment", "date", "start_time", "end_time"]),
            models.Index(fields=["equipment", "status", "start_at", "end_at"]),
        ]
        ordering = ["-date", "start_time"]

    def __str__(self):
        return f"{self.equipment.name} {self.date} {self.start_time}-{self.end_time} ({self.get_status_display()})"

    def get_effective_start_at(self):
        if self.start_at:
            return self.start_at
        if self.date and self.start_time:
            return build_local_aware_datetime(self.date, self.start_time)
        return None

    def get_effective_end_at(self):
        if self.end_at:
            return self.end_at
        if self.date and self.end_time:
            return build_local_aware_datetime(self.date, self.end_time)
        return None

    def get_xrd_remote_connect_availability(self, anchor=None):
        equipment = getattr(self, "equipment", None)
        if not equipment or not equipment.is_xrd():
            return False, "当前预约不是 XRD 预约。"
        if self.status != "active":
            return False, "当前预约不能使用 XRD 远程连接。"
        if self.xrd_test_ended_at:
            return False, "该 XRD 预约已结束测试。"

        start_at = self.get_effective_start_at()
        end_at = self.get_effective_end_at()
        now = get_controlled_now(anchor=anchor)
        if not start_at or not end_at:
            return False, "预约开始时间或结束时间不完整。"
        if now >= end_at:
            return False, "XRD 预约时段已结束。"
        if start_at <= now < end_at:
            return True, ""

        if now < start_at:
            prior_unended_bookings = Booking.objects.filter(
                equipment=equipment,
                status="active",
                start_at__lt=start_at,
                end_at__gt=now,
            ).exclude(pk=self.pk)
            if not prior_unended_bookings.exists():
                return False, "仅在自己的 XRD 预约时段内可连接。"
            unfinished_prior_exists = prior_unended_bookings.filter(xrd_test_ended_at__isnull=True).exists()
            if unfinished_prior_exists:
                return False, "前序 XRD 预约尚未结束测试。"
            return True, ""

        return False, "未在可远程连接的 XRD 预约时间内。"

    def is_today_last_xrd_booking(self, anchor=None):
        equipment = getattr(self, "equipment", None)
        if not equipment or not equipment.is_xrd() or self.status != "active":
            return False

        start_at = self.get_effective_start_at()
        if not start_at:
            return False

        today = get_controlled_today(anchor=anchor)
        if timezone.localtime(start_at).date() != today:
            return False

        day_start = build_local_aware_datetime(today, dt_time.min)
        day_end = day_start + timedelta(days=1)
        last_booking_id = (
            Booking.objects.filter(
                equipment=equipment,
                status="active",
                start_at__gte=day_start,
                start_at__lt=day_end,
            )
            .order_by("-start_at", "-end_at", "-id")
            .values_list("id", flat=True)
            .first()
        )
        return last_booking_id == self.pk

    def save(self, *args, **kwargs):
        equipment = getattr(self, "equipment", None)
        if equipment and self.date and self.start_time:
            self.start_at = build_local_aware_datetime(self.date, self.start_time)
            if equipment.is_planetary_ball_mill():
                if self.actual_duration_minutes:
                    self.end_at = self.start_at + timedelta(minutes=self.actual_duration_minutes)
                    self.end_time = timezone.localtime(self.end_at).time().replace(second=0, microsecond=0)
            elif equipment.is_xrd():
                if self.end_time:
                    self.end_at = build_local_aware_datetime(self.date, self.end_time)
                elif self.actual_duration_minutes:
                    self.end_at = self.start_at + timedelta(minutes=self.actual_duration_minutes)
                    self.end_time = timezone.localtime(self.end_at).time().replace(second=0, microsecond=0)
                if self.start_at and self.end_at:
                    self.actual_duration_minutes = max(
                        int((self.end_at - self.start_at).total_seconds() // 60),
                        0,
                    )
            elif self.end_time:
                self.end_at = build_local_aware_datetime(self.date, self.end_time)
                start_minutes = self.start_time.hour * 60 + self.start_time.minute
                end_minutes = self.end_time.hour * 60 + self.end_time.minute
                self.actual_duration_minutes = max(end_minutes - start_minutes, 0)
        super().save(*args, **kwargs)

    def clean(self):
        """
        统一的业务校验：
        1. 日期不能小于今天；
        2. 日期不能超过可提前预约天数（这里仍按普通 max_advance_days 处理）；
        3. 对齐时间粒度；
        4. 在仪器开放时间范围内；
        5. 开始时间要早于结束时间；
        6. 当天不能预约已经过去的时间段；
        7. 不与其他 active 预约重叠。
        """
        # 当前日期 / 时间
        today = get_controlled_today()
        now = get_controlled_now()

        equipment = self.equipment
        unit = equipment.time_unit_minutes
        open_time_start = dt_time(0, 0) if equipment.is_electrochemical_workstation() else equipment.open_time_start
        open_time_end = dt_time(23, 59) if equipment.is_electrochemical_workstation() else equipment.open_time_end

        def to_minutes(t):
            return t.hour * 60 + t.minute

        start_at = self.start_at
        end_at = self.end_at
        if not start_at and self.date and self.start_time:
            start_at = build_local_aware_datetime(self.date, self.start_time)
        if not end_at:
            if equipment.is_planetary_ball_mill() and start_at and self.actual_duration_minutes:
                end_at = start_at + timedelta(minutes=self.actual_duration_minutes)
            elif equipment.is_xrd() and self.date and self.end_time:
                end_at = build_local_aware_datetime(self.date, self.end_time)
            elif equipment.is_xrd() and start_at and self.actual_duration_minutes:
                end_at = start_at + timedelta(minutes=self.actual_duration_minutes)
            elif self.date and self.end_time:
                end_at = build_local_aware_datetime(self.date, self.end_time)

        if not start_at or not end_at:
            raise ValidationError("预约开始时间或结束时间不完整。")

        # 1. 日期不能小于今天
        if self.date < today:
            raise ValidationError("日期不能小于今天。")

        # 2. 日期不能超过可提前预约天数（模型层使用普通天数；
        #    早鸟逻辑在 API 层按用户单独放宽）
        max_days = self.equipment.max_advance_days
        if max_days is not None:
            latest_date = today + timedelta(days=max_days)
            if self.date > latest_date:
                raise ValidationError(f"最多只能提前 {max_days} 天预约。")

        # 3. 确保时间选择按时间粒度对齐
        if to_minutes(self.start_time) % unit != 0:
            raise ValidationError(f"开始时间需按 {unit} 分钟粒度对齐。")
        if self.start_time < open_time_start or self.start_time >= open_time_end:
            raise ValidationError(
                f"开始时间必须在开放时间 {open_time_start} - {open_time_end} 之间。"
            )

        if equipment.is_xrd():
            if (
                self.end_time
                and to_minutes(self.end_time) % unit != 0
                and self.end_time != open_time_end
            ):
                raise ValidationError(f"结束时间需按 {unit} 分钟粒度对齐。")
            local_end_at = timezone.localtime(end_at)
            if local_end_at.date() != self.date or local_end_at.time() > open_time_end:
                raise ValidationError(
                    f"预约时间必须在开放时间 {open_time_start} - {open_time_end} 之间。"
                )
            if self.end_time and self.start_time >= self.end_time:
                raise ValidationError("开始时间必须早于结束时间。")
            actual_duration_minutes = int((end_at - start_at).total_seconds() // 60)
            if actual_duration_minutes <= 0:
                raise ValidationError("请选择有效的预约占用时段。")
            self.actual_duration_minutes = actual_duration_minutes
            self.xrd_measurement_mode = ""
            self.xrd_scan_speed = None
            self.xrd_scan_range_start = None
            self.xrd_scan_range_end = None
        elif equipment.is_planetary_ball_mill():
            if self.start_time.minute != 0 or self.start_time.second != 0:
                raise ValidationError("行星球磨机仅支持整点开始预约。")
            if self.position_no not in range(1, equipment.get_ball_mill_position_count() + 1):
                raise ValidationError("行星球磨机工位号必须为 1-4。")
            if not self.operation_type:
                raise ValidationError("请选择球磨用途。")
            equipment.validate_ball_mill_rotation_speed_rpm(self.rotation_speed_rpm)
            if not self.milling_minutes:
                raise ValidationError("请填写球磨时间。")
            expected_actual_minutes = equipment.calculate_ball_mill_actual_minutes(self.milling_minutes)
            if self.actual_duration_minutes != expected_actual_minutes:
                raise ValidationError("真实预约时长与球磨时间换算结果不一致。")
            if self.actual_duration_minutes > equipment.ball_mill_max_actual_minutes:
                raise ValidationError(
                    f"单次真实预约时长不能超过 {equipment.ball_mill_max_actual_minutes} 分钟。"
                )
        else:
            is_terminal_electrochemical_end = (
                equipment.is_electrochemical_workstation()
                and self.end_time == open_time_end
            )
            if to_minutes(self.end_time) % unit != 0 and not is_terminal_electrochemical_end:
                raise ValidationError(f"结束时间需按 {unit} 分钟粒度对齐。")

            # 4. 必须在仪器开放时间范围内
            if self.start_time < open_time_start or self.end_time > open_time_end:
                raise ValidationError(
                    f"预约时间必须在开放时间 {open_time_start} - {open_time_end} 之间。"
                )

            # 5. 确保开始时间在结束时间之前
            if self.start_time >= self.end_time:
                raise ValidationError("开始时间必须早于结束时间。")

            if equipment.is_electrochemical_workstation():
                if self.position_no not in range(1, equipment.get_electrochemical_channel_count() + 1):
                    raise ValidationError("请选择通道 1-8。")
                if self.position_no in equipment.get_electrochemical_offline_channel_set():
                    raise ValidationError(f"通道 {self.position_no} 当前已暂时下线。")

        # 6. 不能预约已经结束的时间段；当前所处时段仍可预约。
        if end_at <= now:
            raise ValidationError("当前时间之前的时间段不能预约。")

        # 7. 确保时间段不与其他预约冲突（只看 active）
        overlapping_bookings = Booking.objects.filter(
            equipment=self.equipment,
            status="active",
            start_at__lt=end_at,
            end_at__gt=start_at,
        )
        # 编辑场景要排除自己
        if self.pk:
            overlapping_bookings = overlapping_bookings.exclude(pk=self.pk)

        if equipment.is_planetary_ball_mill():
            overlapping_bookings = list(overlapping_bookings.select_related("user"))
            if any(booking.position_no == self.position_no for booking in overlapping_bookings):
                raise ValidationError(f"{self.position_no} 号位在该时间段已被预约。")

            speeds = {booking.rotation_speed_rpm for booking in overlapping_bookings if booking.rotation_speed_rpm}
            if len(speeds) > 1:
                raise ValidationError(
                    "当前预约时长跨越了多个不同锁速区段，"
                    "请缩短球磨时间或调整开始时间/工位。"
                )

            locked_speed = next(iter(speeds), None)
            if locked_speed and self.rotation_speed_rpm != locked_speed:
                raise ValidationError(
                    f"当前时段已锁定为 {locked_speed} r/min，仅能预约相同转速的空闲工位。"
                )

            if len(overlapping_bookings) >= equipment.get_ball_mill_position_count():
                raise ValidationError("该时间段 4 个工位均已被预约。")
        elif equipment.is_electrochemical_workstation():
            overlapping_bookings = list(overlapping_bookings)
            if any(booking.position_no == self.position_no for booking in overlapping_bookings):
                raise ValidationError(f"通道 {self.position_no} 在该时间段已被预约。")
        elif overlapping_bookings.exists():
            raise ValidationError("该时间段已有预约，请选择其他时间。")


class BallMillQueueRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ALLOCATED = "allocated"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_PENDING, "排队中"),
        (STATUS_ALLOCATED, "已分配"),
        (STATUS_REJECTED, "未分配"),
        (STATUS_CANCELLED, "已取消"),
    )

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.CASCADE,
        related_name="ball_mill_queue_requests",
        verbose_name="仪器",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ball_mill_queue_requests",
        verbose_name="申请人",
    )
    requested_date = models.DateField("期望日期")
    requested_start_time = models.TimeField("期望开始时间")
    position_count = models.PositiveSmallIntegerField("需求工位数", default=1)
    operation_type = models.CharField(
        "操作类型",
        max_length=20,
        choices=Booking.OPERATION_TYPE_CHOICES,
    )
    rotation_speed_rpm = models.PositiveIntegerField("转速(r/min)")
    milling_minutes = models.PositiveIntegerField("球磨时间(分钟)")
    actual_duration_minutes = models.PositiveIntegerField("真实预约时长(分钟)")
    remark = models.CharField("备注", max_length=200, blank=True, default="")

    status = models.CharField(
        "状态",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    fail_reason = models.CharField("失败原因", max_length=200, blank=True, default="")

    allocated_start_at = models.DateTimeField("分配开始时间", null=True, blank=True)
    allocated_end_at = models.DateTimeField("分配结束时间", null=True, blank=True)
    allocated_position_nos = models.JSONField("分配工位", default=list, blank=True)
    allocated_booking_ids = models.JSONField("分配预约ID", default=list, blank=True)
    dispatched_at = models.DateTimeField("放榜时间", null=True, blank=True)
    created_at = models.DateTimeField("申请时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "球磨排队申请"
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=["equipment", "status", "requested_date", "requested_start_time"]),
            models.Index(fields=["equipment", "user", "status", "created_at"]),
        ]
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.equipment.name} {self.user_id} {self.requested_date} {self.status}"

    def clean(self):
        if not self.equipment or not self.equipment.is_planetary_ball_mill():
            raise ValidationError("仅行星球磨机支持排队申请。")
        if self.position_count not in range(1, self.equipment.get_ball_mill_position_count() + 1):
            raise ValidationError("需求工位数必须为 1-4。")
        self.equipment.validate_ball_mill_rotation_speed_rpm(self.rotation_speed_rpm)
        if self.milling_minutes <= 0:
            raise ValidationError("球磨时间必须大于 0。")
        expected = self.equipment.calculate_ball_mill_actual_minutes(self.milling_minutes)
        if self.actual_duration_minutes != expected:
            raise ValidationError("真实预约时长与球磨时间换算结果不一致。")
        if self.actual_duration_minutes > self.equipment.ball_mill_max_actual_minutes:
            raise ValidationError(
                f"真实预约时长不能超过 {self.equipment.ball_mill_max_actual_minutes} 分钟。"
            )
