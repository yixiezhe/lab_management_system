from django.db import models

from users.models import UserProfile


def default_duty_schedule():
    return [
        {"weekday": 0, "user_id": None, "name": ""},
        {"weekday": 1, "user_id": None, "name": ""},
        {"weekday": 2, "user_id": None, "name": ""},
        {"weekday": 3, "user_id": None, "name": ""},
        {"weekday": 4, "user_id": None, "name": ""},
        {"weekday": 5, "user_id": None, "name": ""},
        {"weekday": 6, "user_id": None, "name": ""},
    ]


class GroupAffairBoard(models.Model):
    tutor = models.OneToOneField(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="group_affair_board",
        verbose_name="导师",
    )
    text_content = models.TextField(blank=True, verbose_name="事务文本")
    duty_schedule = models.JSONField(default=default_duty_schedule, verbose_name="值日表")
    duty_reminder_enabled = models.BooleanField(default=False, verbose_name="启用每日值日弹窗提醒")
    purchase_rotation = models.JSONField(default=list, blank=True, verbose_name="采购轮班名单")
    purchase_rotation_index = models.PositiveIntegerField(default=0, verbose_name="下次采购轮班序号")
    updated_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_group_affair_boards",
        verbose_name="最后修改人",
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    def __str__(self):
        return f"{self.tutor.name}小组事务"

    class Meta:
        verbose_name = "小组事务板"
        verbose_name_plural = verbose_name
        ordering = ["tutor__name", "id"]


class GroupAffairAdmin(models.Model):
    tutor = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="group_affair_admin_groups",
        verbose_name="导师",
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="group_affair_adminships",
        verbose_name="小组管理员",
    )
    assigned_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_group_affair_admins",
        verbose_name="任命人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="任命时间")

    def __str__(self):
        return f"{self.tutor.name}小组管理员 - {self.user.name}"

    class Meta:
        verbose_name = "小组事务管理员"
        verbose_name_plural = verbose_name
        unique_together = ("tutor", "user")
        ordering = ["tutor__name", "user__name", "id"]


class GroupAffairNotice(models.Model):
    board = models.ForeignKey(
        GroupAffairBoard,
        on_delete=models.CASCADE,
        related_name="notices",
        verbose_name="小组事务板",
    )
    title = models.CharField(max_length=120, default="小组提醒", verbose_name="提醒标题")
    content = models.TextField(verbose_name="提醒内容")
    created_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_group_affair_notices",
        verbose_name="发布人",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")

    def __str__(self):
        return f"{self.board} - {self.title}"

    class Meta:
        verbose_name = "小组事务弹窗提醒"
        verbose_name_plural = verbose_name
        ordering = ["-created_at", "-id"]


class GroupAffairNoticeRead(models.Model):
    notice = models.ForeignKey(
        GroupAffairNotice,
        on_delete=models.CASCADE,
        related_name="read_records",
        verbose_name="提醒",
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="group_affair_notice_reads",
        verbose_name="用户",
    )
    read_at = models.DateTimeField(auto_now=True, verbose_name="阅读时间")

    def __str__(self):
        return f"{self.user.name} 已读 {self.notice.title}"

    class Meta:
        verbose_name = "小组事务提醒阅读记录"
        verbose_name_plural = verbose_name
        unique_together = ("notice", "user")
        ordering = ["-read_at"]


class GroupAffairDutyReminderRead(models.Model):
    board = models.ForeignKey(
        GroupAffairBoard,
        on_delete=models.CASCADE,
        related_name="duty_reminder_reads",
        verbose_name="小组事务板",
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="group_affair_duty_reminder_reads",
        verbose_name="用户",
    )
    duty_date = models.DateField(verbose_name="值日日期")
    read_at = models.DateTimeField(auto_now=True, verbose_name="提醒确认时间")

    def __str__(self):
        return f"{self.user.name} {self.duty_date} 值日提醒已确认"

    class Meta:
        verbose_name = "小组值日提醒确认记录"
        verbose_name_plural = verbose_name
        unique_together = ("board", "user", "duty_date")
        ordering = ["-duty_date", "-read_at"]


class GroupPurchase(models.Model):
    STATUS_ASSIGNED = "assigned"
    STATUS_PAID = "paid"
    STATUS_ARRIVED = "arrived"
    STATUS_REIMBURSED = "reimbursed"
    STATUS_CHOICES = [
        (STATUS_ASSIGNED, "待购买"),
        (STATUS_PAID, "已支付"),
        (STATUS_ARRIVED, "已到货"),
        (STATUS_REIMBURSED, "已报销"),
    ]

    board = models.ForeignKey(GroupAffairBoard, on_delete=models.CASCADE, related_name="purchases", verbose_name="小组事务板")
    requester = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="requested_group_purchases", verbose_name="请购人")
    buyer = models.ForeignKey(UserProfile, on_delete=models.PROTECT, related_name="assigned_group_purchases", verbose_name="采购人")
    items = models.TextField(verbose_name="采购物品")
    note = models.TextField(blank=True, verbose_name="备注")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ASSIGNED, verbose_name="状态")
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="支付金额")
    payment_proof = models.FileField(upload_to="group_purchases/payment/%Y/%m/", blank=True, verbose_name="支付凭证")
    invoice = models.FileField(upload_to="group_purchases/invoice/%Y/%m/", blank=True, verbose_name="发票")
    item_image = models.ImageField(upload_to="group_purchases/items/%Y/%m/", blank=True, verbose_name="实物图片")
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name="支付时间")
    arrived_at = models.DateTimeField(null=True, blank=True, verbose_name="到货登记时间")
    reimbursed_at = models.DateTimeField(null=True, blank=True, verbose_name="报销完成时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发起时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "组内采购"
        verbose_name_plural = verbose_name
        ordering = ["-created_at", "-id"]


class GroupPurchasePopupRead(models.Model):
    TYPE_ASSIGNED = "assigned"
    TYPE_REIMBURSEMENT = "reimbursement"
    TYPE_CHOICES = [(TYPE_ASSIGNED, "采购分配提醒"), (TYPE_REIMBURSEMENT, "报销提醒")]

    purchase = models.ForeignKey(GroupPurchase, on_delete=models.CASCADE, related_name="popup_reads", verbose_name="采购单")
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="group_purchase_popup_reads", verbose_name="用户")
    reminder_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="提醒类型")
    reminder_date = models.DateField(verbose_name="提醒日期")
    read_at = models.DateTimeField(auto_now=True, verbose_name="确认时间")

    class Meta:
        verbose_name = "组内采购弹窗确认"
        verbose_name_plural = verbose_name
        constraints = [
            models.UniqueConstraint(fields=["purchase", "user", "reminder_type", "reminder_date"], name="unique_group_purchase_popup_read")
        ]
