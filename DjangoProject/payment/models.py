from io import BytesIO
import os
from django.core.files.base import ContentFile
from PIL import Image
from django.db import models
from procurement.models import PurchaseRequest
from users.models import UserProfile
from datetime import datetime # <--- 【新增点 1】导入datetime模块

def payment_photo_path(instance, filename):
    # 【修改点 2】使用 datetime.now() 来获取当前时间，而不是 instance.paid_at
    # 文件将上传到 MEDIA_ROOT/payments/YYYY/MM/DD/<purchase_request_id>_<filename>
    return f'payments/{datetime.now().strftime("%Y/%m/%d")}/{instance.purchase_request.id}_{filename}'

class Payment(models.Model):
    # 使用 OneToOneField 确保一个采购申请只对应一个支付记录
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='payment', # 允许我们通过 purchase_request.payment 访问
        verbose_name="关联的采购申请"
    )
    payment_photo = models.ImageField(upload_to=payment_photo_path, verbose_name="支付截图")
    paid_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="支付人"
    )
    paid_at = models.DateTimeField(auto_now_add=True, verbose_name="支付时间")

    def save(self, *args, **kwargs):
        # Convert TIFF payment images to PNG for browser compatibility.
        if self.payment_photo and hasattr(self.payment_photo, 'file') and not getattr(self.payment_photo, '_committed', True):
            name = self.payment_photo.name or ''
            ext = os.path.splitext(name)[1].lower()
            if ext in ('.tif', '.tiff'):
                try:
                    self.payment_photo.file.seek(0)
                    img = Image.open(self.payment_photo.file)
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    buffer.seek(0)
                    new_name = os.path.splitext(name)[0] + '.png'
                    self.payment_photo.save(new_name, ContentFile(buffer.read()), save=False)
                except Exception:
                    # Fall back to original upload if conversion fails.
                    pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"支付记录 for {self.purchase_request.id}"

    class Meta:
        verbose_name = "支付记录"
        verbose_name_plural = verbose_name