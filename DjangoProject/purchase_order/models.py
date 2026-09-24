# DjangoProject/purchase_order/models.py

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from procurement.models import PurchaseRequest
from users.models import UserProfile

class PurchaseOrder(models.Model):
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='purchase_order',
        verbose_name="关联的采购申请"
    )
    po_form = models.FileField(upload_to='purchase_orders/%Y/%m/%d/', verbose_name="请购单文件")
    uploaded_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        verbose_name="上传人"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    class Meta:
        verbose_name = "请购单"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"请购单 (关联采购ID: {self.purchase_request.id})"

@receiver(post_save, sender=PurchaseOrder)
def update_purchase_request_status_on_po_save(sender, instance, **kwargs):
    """
    在请购单创建或更新后，自动更新关联采购申请的状态。
    """
    purchase_request = instance.purchase_request
    if purchase_request.status == 'pending_purchase_order':
        purchase_request.status = 'pending_contract'
        purchase_request.save(update_fields=['status'])