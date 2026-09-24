from django.db import models
from procurement.models import PurchaseRequest
from users.models import UserProfile


class Acceptance(models.Model):
    """
    收货验收信息模型
    """
    # 同样使用 OneToOneField 与采购申请建立一对一的关联
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='acceptance',  # 允许我们通过 purchase_request.acceptance 访问
        verbose_name="关联的采购申请"
    )

    receiving_status = models.TextField(verbose_name="收货情况")

    # 用于存储验收照片
    acceptance_photo = models.ImageField(
        upload_to='acceptances/%Y/%m/%d/',
        verbose_name="验收照片",
        blank=True,  # 设为可选
        null=True
    )

    # 记录由谁填写的验收信息
    recorded_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        verbose_name="记录人"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "收货验收信息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"验收记录 (关联采购ID: {self.purchase_request.id})"
