from django.db import models
from users.models import UserProfile
import uuid


class TeamPurchaseRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', '待审批'),
        ('approved', '已批准'),
        ('rejected', '已驳回'),
        ('completed', '已完成'),
        ('withdrawn', '已撤回'), # <--- 【新增点】
    ]

    applicant = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="申请人")
    tutor = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_requests',
        verbose_name="所属导师"
    )
    request_date = models.DateField(auto_now_add=True, verbose_name="申请日期")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="总价")

    approved_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_approved_requests',
        verbose_name="审批人"
    )
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="驳回原因")

    def save(self, *args, **kwargs):
        if self.applicant and self.applicant.assigned_tutor:
            self.tutor = self.applicant.assigned_tutor
        super().save(*args, **kwargs)

    def __str__(self):
        return f"小组请购 - {self.applicant.name} - {self.request_date}"

    class Meta:
        verbose_name = "小组请购申请"
        verbose_name_plural = verbose_name


class TeamRequestItem(models.Model):
    purchase_request = models.ForeignKey(TeamPurchaseRequest, related_name='items', on_delete=models.CASCADE,
                                         verbose_name="所属申请")
    content = models.CharField(max_length=200, verbose_name="采购内容")
    specifications = models.CharField(max_length=200, blank=True, null=True, verbose_name="规格")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="单价")
    quantity = models.PositiveIntegerField(verbose_name="数量")
    purchase_link = models.URLField(blank=True, null=True, verbose_name="采购链接(选填)")

    def __str__(self):
        return self.content

    class Meta:
        verbose_name = "小组采购物品"
        verbose_name_plural = verbose_name