from django.db import models
# --- 【新】导入 PurchaseRequest 和 UserProfile ---
from procurement.models import PurchaseRequest  # 导入主采购申请模型
from users.models import UserProfile  # 导入用户模型


# --- END ---

# 公共经费统计表模型
class PublicExpenseRecord(models.Model):
    # 申请人部分
    date = models.DateField(verbose_name="日期")
    platform = models.CharField(max_length=100, verbose_name="采购平台")
    order_number = models.CharField(max_length=100, unique=True, verbose_name="单号")
    purchase_link = models.URLField(blank=True, null=True, verbose_name="采购链接")
    applicant_name = models.CharField(max_length=100, verbose_name="采购申请人")
    purchase_type = models.CharField(max_length=50, verbose_name="采购类型")
    content = models.CharField(max_length=200, verbose_name="采购内容")
    manufacturer = models.CharField(max_length=200, blank=True, null=True, verbose_name="厂商")
    parameters = models.CharField(max_length=200, blank=True, null=True, verbose_name="参数")
    specifications = models.CharField(max_length=200, blank=True, null=True, verbose_name="规格")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="单价")
    quantity = models.PositiveIntegerField(verbose_name="数量")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="总价")
    tutor_name = models.CharField(max_length=100, verbose_name="申请人导师")

    # 其他部分（暂时留空）
    approver_name = models.CharField(max_length=100, blank=True, null=True, verbose_name="审批及采购人姓名")

    # ... 您提到的其他发票、付款、验收字段 ...

    class Meta:
        verbose_name = "公共经费统计表"
        verbose_name_plural = verbose_name


# 公对公统计表模型（结构类似，字段略有不同）
class C2CExpenseRecord(models.Model):
    # ... 根据您的需求定义类似 PublicExpenseRecord 的字段 ...
    # 例如：
    serial_number = models.AutoField(primary_key=True, verbose_name="序号")
    date = models.DateField(verbose_name="日期")
    platform = models.CharField(max_length=100, verbose_name="采购平台")
    order_number = models.CharField(max_length=100, unique=True, verbose_name="单号")

    # ... 其他您在需求中提到的字段 ...

    class Meta:
        verbose_name = "公对公经费统计表"
        verbose_name_plural = verbose_name


# --- 【新】添加 Reimbursement 模型 ---

def reimbursement_upload_path(instance, filename):
    """
    为上传的报销单照片生成动态路径
    格式: reimbursements/<purchase_request_id>/<filename>
    """
    pr_id = instance.purchase_request.id
    return f'reimbursements/{pr_id}/{filename}'


class Reimbursement(models.Model):
    """
    存储最终报销凭证的模型
    """
    # 关键链接：一对一关联到主采购申请
    purchase_request = models.OneToOneField(
        PurchaseRequest,
        on_delete=models.CASCADE,
        related_name='reimbursement_details',
        verbose_name="关联的采购申请"
    )

    reimbursement_number = models.CharField(
        max_length=100,
        verbose_name="报销单号",
        help_text="财务系统中的报销单号或凭证号"
    )

    actual_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="报销实际金额"
    )

    reimbursement_photo = models.ImageField(
        upload_to=reimbursement_upload_path,
        verbose_name="报销单照片"
    )

    submitted_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="提交人"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    def __str__(self):
        return f"报销单: {self.reimbursement_number} (申请: {self.purchase_request.order_number})"

    class Meta:
        verbose_name = "报销凭证"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

# --- 【新】代码结束 ---
