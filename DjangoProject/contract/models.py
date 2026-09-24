# DjangoProject/contract/models.py

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from procurement.models import PurchaseRequest
from users.models import UserProfile

class Contract(models.Model):
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='contract',
        verbose_name="关联的采购申请"
    )
    contract_form = models.FileField(upload_to='contracts/%Y/%m/%d/', verbose_name="合同文件")
    uploaded_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        verbose_name="上传人"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        verbose_name = "合同"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"合同 (关联采购ID: {self.purchase_request.id})"

@receiver(post_save, sender=Contract)
def update_purchase_request_status_on_contract_save(sender, instance, **kwargs):
    """
    在合同创建或更新后，自动更新关联采购申请的状态。
    """
    purchase_request = instance.purchase_request
    if purchase_request.status == 'pending_contract':
        purchase_request.status = 'paid'  # 'paid' 状态对应“待收货”
        purchase_request.save(update_fields=['status'])