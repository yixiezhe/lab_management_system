from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from procurement.models import PurchaseRequest
from users.models import UserProfile
from io import BytesIO
import os
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image


PDF_CONTENT_TYPES = {'application/pdf', 'application/x-pdf'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tif', '.tiff'}


def validate_invoice_file(file_obj):
    if not file_obj:
        return

    name = getattr(file_obj, 'name', '') or ''
    ext = os.path.splitext(name)[1].lower()
    content_type = (getattr(file_obj, 'content_type', '') or '').lower()
    is_pdf = ext == '.pdf' or content_type in PDF_CONTENT_TYPES
    is_image = ext in IMAGE_EXTENSIONS or content_type.startswith('image/')

    if not is_pdf and not is_image:
        raise ValidationError("请上传图片或PDF格式的发票文件。")

    position = None
    try:
        position = file_obj.tell()
    except Exception:
        pass

    try:
        file_obj.seek(0)
        if is_pdf:
            if file_obj.read(5) != b'%PDF-':
                raise ValidationError("PDF发票文件格式不正确。")
            return

        Image.open(file_obj).verify()
    except ValidationError:
        raise
    except Exception:
        raise ValidationError("请上传有效的图片或PDF发票文件。")
    finally:
        try:
            file_obj.seek(position if position is not None else 0)
        except Exception:
            pass


class Invoice(models.Model):
    """
    发票报销信息模型
    """
    purchase_request = models.ForeignKey(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='invoices',
        verbose_name="关联的采购申请"
    )

    invoice_number = models.CharField(max_length=255, verbose_name="发票单号")
    company_name = models.CharField(max_length=255, verbose_name="发票公司")

    payment_link = models.URLField(max_length=500, blank=True, null=True, verbose_name="付款链接")

    invoice_image = models.FileField(
        upload_to='invoices/%Y/%m/%d/',
        validators=[validate_invoice_file],
        verbose_name="发票截图"
    )
    requires_acceptance = models.BooleanField(default=False, verbose_name="是否需要验收")

    submitted_by = models.ForeignKey(
        UserProfile,
        on_delete=models.PROTECT,
        verbose_name="提交人"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "发票信息"
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        # Convert TIFF invoice images to PNG for browser compatibility.
        if self.invoice_image and hasattr(self.invoice_image, 'file') and not getattr(self.invoice_image, '_committed', True):
            name = self.invoice_image.name or ''
            ext = os.path.splitext(name)[1].lower()
            if ext in ('.tif', '.tiff'):
                try:
                    self.invoice_image.file.seek(0)
                    img = Image.open(self.invoice_image.file)
                    if img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    buffer.seek(0)
                    new_name = os.path.splitext(name)[0] + '.png'
                    self.invoice_image.save(new_name, ContentFile(buffer.read()), save=False)
                except Exception:
                    # Fall back to original upload if conversion fails.
                    pass

        super().save(*args, **kwargs)

    def __str__(self):
        return f"发票号: {self.invoice_number} (关联采购ID: {self.purchase_request.id})"


# --- 【核心修改】重写信号处理器以实现流程分支 ---
@receiver(post_save, sender=Invoice)
def update_purchase_request_status_on_invoice_save(sender, instance, **kwargs):
    """
    在发票信息创建或更新后，根据是否需要验收，智能更新关联采购申请的状态。
    """
    purchase_request = instance.purchase_request

    # 只在当前状态为 'goods_received' (待开票) 时执行状态转换
    if purchase_request.status == 'goods_received':
        # 如果发票标记为“需要验收”
        if instance.requires_acceptance:
            # 则将状态更新为 'invoiced' (流转到“待验收”环节)
            purchase_request.status = 'invoiced'
        # 如果发票标记为“无需验收”
        else:
            # 则将状态更新为 'inspection_skipped' (直接跳到“待报销”环节)
            purchase_request.status = 'inspection_skipped'

        # 保存状态更新
        purchase_request.save(update_fields=['status'])
