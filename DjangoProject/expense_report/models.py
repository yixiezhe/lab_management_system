# expense_report/models.py
from django.db import models
from procurement.models import PurchaseRequest
from users.models import UserProfile

class ExpenseReport(models.Model):
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='expense_report',
        verbose_name="关联的采购申请"
    )
    reimbursement_form = models.FileField(upload_to='reimbursements/%Y/%m/%d/', verbose_name="报销单据")
    submitted_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        verbose_name="提交人"
    )
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="提交时间")

    class Meta:
        verbose_name = "经费报销"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"报销单 (关联采购ID: {self.purchase_request.id})"
        return f"报销单 (关联采购ID: {self.purchase_request.id})"