# procurement/models.py
from django.db import models
from users.models import UserProfile  # Make sure UserProfile is imported correctly
from django.db import transaction
from django.db.models import Max
from datetime import date

import uuid

MAIN_CATEGORY_CHOICES = [('c2c', '公对公'), ('public', '公共经费')]

def default_public_duty_schedule():
    return [
        {"weekday": 0, "name": "示例成员26"},
        {"weekday": 1, "name": "示例成员22"},
        {"weekday": 2, "name": "示例成员24"},
        {"weekday": 3, "name": "示例成员26"},
        {"weekday": 4, "name": "示例成员07"},
        {"weekday": 5, "name": "示例成员11"},
        {"weekday": 6, "name": "示例成员05"},
    ]



class WhitelistItem(models.Model):
    PURCHASE_TYPE_CHOICES = [
        ('consumable', '耗材'), ('chemical', '药品'), ('equipment', '设备'), ('other', '其他')
    ]

    content = models.CharField(max_length=200, verbose_name="采购内容", unique=True)
    main_category = models.JSONField(verbose_name="主分类", default=list)
    platform = models.CharField(max_length=100, verbose_name="平台/服务", blank=True, null=True)
    purchase_type = models.CharField(max_length=20, choices=PURCHASE_TYPE_CHOICES, verbose_name="采购类型")
    manufacturer = models.CharField(max_length=200, blank=True, null=True, verbose_name="厂商")
    cas_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="CAS号")
    product_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="货号")
    parameters = models.CharField(max_length=200, blank=True, null=True, verbose_name="参数")
    specifications = models.CharField(max_length=200, blank=True, null=True, verbose_name="规格")

    def __str__(self):
        return self.content

    class Meta:
        verbose_name = "白名单项目"
        verbose_name_plural = verbose_name


class PurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', '待审批'),
        ('rejected', '已驳回'),
        ('withdrawn', '已撤回'),
        ('payment_rejected', '付款已驳回'),
        ('pending_purchase_order', '待请购'),
        ('pending_contract', '待合同'),
        ('approved', '待支付'),
        ('paid', '待收货'),
        ('goods_received', '待开票'),
        ('invoiced', '待验收'),
        ('accepted', '待报销'),
        ('inspection_skipped', '待报销 (无需验收)'),
        ('reimbursed', '已报销'),
        ('merged', '已合并'),
        ('completed', '已完成'),
    ]
    applicant = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="申请人")
    request_date = models.DateField(auto_now_add=True, verbose_name="申请日期")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    merged_from_status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        null=True,
        blank=True,
        verbose_name="合并前状态"
    )
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="驳回原因")

    parent_request = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='merged_children',
        verbose_name="合并后的父申请"
    )

    approved_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests',
        verbose_name="审批人"
    )
    approval_date = models.DateField(verbose_name="批准日期", null=True, blank=True, db_index=True)

    # --- START OF MODIFICATION ---
    handler = models.ForeignKey(
        UserProfile,  # Assuming your user model is UserProfile in users app
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='处理人',
        related_name='handled_purchase_requests',
        help_text='记录批准此申请并负责后续流程的用户'
    )
    # --- END OF MODIFICATION ---

    expense_type = models.CharField(max_length=50, verbose_name="经费类型",
                                     choices=[('c2c', '公对公'), ('public', '公共经费')])
    platform = models.CharField(max_length=100, verbose_name="平台")
    order_number = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="单号")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="总价")
    actual_payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="实际支付金额"
    )
    applicant_tutor = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='supervised_requests', verbose_name="申请人导师")

    def __str__(self):
        return f"{self.applicant.name} - {self.request_date} - {self.get_expense_type_display()}"

    def save(self, *args, **kwargs):
        if self.applicant and self.applicant.assigned_tutor:
            self.applicant_tutor = self.applicant.assigned_tutor
        super().save(*args, **kwargs)

    @property
    def latest_invoice(self):
        # Use prefetched invoices when available to avoid extra queries.
        prefetched = getattr(self, '_prefetched_objects_cache', {}).get('invoices')
        if prefetched is not None:
            if not prefetched:
                return None
            return max(prefetched, key=lambda inv: inv.created_at or inv.id)
        return self.invoices.order_by('-created_at').first()

    class Meta:
        verbose_name = "采购申请"
        verbose_name_plural = verbose_name

    # ========= 新增：原子化单号生成 =========
    @classmethod
    def generate_order_number_atomic(cls, platform: str, prefix: str, the_date: date):
        """
        在事务中为给定平台/日期生成递增且唯一的单号。
        形如: <prefix><YYYYMMDD><NN>  (NN 为两位序号)
        必须在外层 transaction.atomic() 中调用。
        """
        base = f"{prefix}{the_date.strftime('%Y%m%d')}"
        # 加锁当日该平台下所有已分配单号的行，避免并发取同一个最大值。
        qs = (
            cls.objects
            .select_for_update()
            .filter(platform=platform, order_number__startswith=base)
            .order_by('-order_number')
        )
        last = qs.values_list('order_number', flat=True).first()
        if last:
            try:
                seq = int(last[-2:]) + 1
            except ValueError:
                # 兜底：若尾部不是数字，从 1 开始
                seq = 1
        else:
            seq = 1
        return f"{base}{seq:02d}"


class RequestItem(models.Model):
    purchase_request = models.ForeignKey(PurchaseRequest, related_name='items', on_delete=models.CASCADE,
                                         verbose_name="所属申请")
    source_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='source_items',
        verbose_name="合并前所属申请"
    )
    original_applicant = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='original_request_items',
        verbose_name="原始申请人"
    )

    purchase_type = models.CharField(max_length=50, verbose_name="采购类型",
                                     choices=[('consumable', '耗材'), ('chemical', '药品'), ('repair', '维修服务'),
                                              ('other', '其他')])
    content = models.CharField(max_length=200, verbose_name="采购内容")
    manufacturer = models.CharField(max_length=200, blank=True, null=True, verbose_name="厂商")
    parameters = models.CharField(max_length=200, blank=True, null=True, verbose_name="参数")
    cas_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="CAS号")
    product_number = models.CharField(max_length=50, blank=True, null=True, verbose_name="货号")
    purchase_link = models.TextField(blank=True, null=True, verbose_name="采购链接")
    specifications = models.CharField(max_length=200, blank=True, null=True, verbose_name="规格")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="单价")
    quantity = models.PositiveIntegerField(verbose_name="数量")

    def __str__(self):
        return self.content

    class Meta:
        verbose_name = "采购物品"
        verbose_name_plural = verbose_name


class Platform(models.Model):
    CATEGORY_CHOICES = [
        ('c2c', '公对公'),
        ('public', '公共经费'),
    ]
    name = models.CharField(max_length=100, unique=True, verbose_name="平台名称")
    prefix = models.CharField(max_length=1, unique=True, blank=True, null=True, verbose_name="单号前缀(单个大写字母)")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="所属经费类型")

    managers = models.ManyToManyField(
        UserProfile,
        related_name='managed_platforms',
        blank=True,
        verbose_name="平台负责人"
    )

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"

    class Meta:
        verbose_name = "采购平台"
        verbose_name_plural = verbose_name
        ordering = ['category', 'name']


class GlobalAnnouncement(models.Model):
    """
    公告记录。历史上该模型是单例公告，现在改为支持多条公告。
    """
    title = models.CharField(max_length=120, default="公告", verbose_name="公告标题")
    content = models.TextField(blank=True, verbose_name="公告内容")
    is_published = models.BooleanField(default=False, verbose_name="在首页展示")
    show_popup = models.BooleanField(default=False, verbose_name="登录时弹窗显示")
    created_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_announcements",
        verbose_name="发布人"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="发布时间")
    updated_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_announcements",
        verbose_name="最后修改人"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    @classmethod
    def load(cls):
        obj = cls.objects.order_by("-updated_at", "-id").first()
        if obj is None:
            obj = cls.objects.create(title="公告")
        return obj

    def __str__(self):
        return self.title or "公告"

    class Meta:
        verbose_name = "公告"
        verbose_name_plural = verbose_name
        ordering = ["-created_at", "-id"]


class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(
        GlobalAnnouncement,
        on_delete=models.CASCADE,
        related_name="read_records",
        verbose_name="公告"
    )
    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        related_name="announcement_reads",
        verbose_name="用户"
    )
    read_at = models.DateTimeField(auto_now=True, verbose_name="阅读时间")

    class Meta:
        verbose_name = "公告阅读记录"
        verbose_name_plural = verbose_name
        unique_together = ("announcement", "user")
        ordering = ["-read_at"]

    def __str__(self):
        return f"{self.user} 已读 {self.announcement}"


class PublicProcurementDutySchedule(models.Model):
    """
    公共经费采购流程中“每周采购人”单例配置。
    """
    weekly_duty = models.JSONField(default=default_public_duty_schedule, verbose_name="每周采购人")
    updated_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="最后修改人"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "公共经费采购每周采购人设置"

    class Meta:
        verbose_name = "公共经费采购每周采购人设置"
        verbose_name_plural = verbose_name
