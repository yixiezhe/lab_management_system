from django.db import models
from procurement.models import PurchaseRequest
from users.models import UserProfile


class Inspection(models.Model):
    """
    采购验收信息模型
    """
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='inspection',
        verbose_name="关联的采购申请"
    )
    inspection_number = models.CharField(max_length=255, verbose_name="验收单号")
    inspection_photo = models.ImageField(upload_to='inspections/%Y/%m/%d/', verbose_name="验收照片")

    inspector = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        verbose_name="验收人"
    )
    inspected_at = models.DateTimeField(auto_now_add=True, verbose_name="验收时间")

    class Meta:
        verbose_name = "验收信息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"验收单: {self.inspection_number} (关联采购ID: {self.purchase_request.id})"