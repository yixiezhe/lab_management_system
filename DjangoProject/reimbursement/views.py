from rest_framework import viewsets, permissions, status
from .models import PublicExpenseRecord, C2CExpenseRecord, Reimbursement  # --- 【新】导入 Reimbursement
from .serializers import PublicExpenseRecordSerializer, C2CExpenseRecordSerializer, \
    ReimbursementSerializer  # --- 【新】导入 ReimbursementSerializer
from procurement.permissions import IsApprover  # 从procurement应用导入IsApprover权限


class PublicExpenseRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    只读视图集，用于提供公共经费统计记录。
    """
    queryset = PublicExpenseRecord.objects.all().order_by('-date')
    serializer_class = PublicExpenseRecordSerializer
    permission_classes = [IsApprover]  # 只有审批者才能访问


class C2CExpenseRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """
    只读视图集，用于提供公对公经费统计记录。
    """
    queryset = C2CExpenseRecord.objects.all().order_by('-date')
    serializer_class = C2CExpenseRecordSerializer
    permission_classes = [IsApprover]  # 只有审批者才能访问


# --- 【新】添加 Reimbursement ViewSet ---
class ReimbursementViewSet(viewsets.ModelViewSet):
    """
    视图集，用于创建和管理报销凭证。
    """
    queryset = Reimbursement.objects.all().order_by('-created_at')
    serializer_class = ReimbursementSerializer
    permission_classes = [IsApprover]  # 只有审批者（或有权访问待报销页面的用户）才能操作

    def perform_create(self, serializer):
        """
        在创建报销凭证后，自动执行两个操作：
        1. 将提交人 (submitted_by) 设置为当前请求的用户。
        2. 将关联的 PurchaseRequest 状态更新为 'reimbursed' (已报销)。
        """
        # 1. 保存报销凭证实例
        reimbursement_instance = serializer.save(submitted_by=self.request.user)

        # 2. 获取关联的采购申请
        purchase_request = reimbursement_instance.purchase_request

        # 3. 更新采购申请的状态
        if not purchase_request:
            return

        # 如果是合并后的子申请，保留子申请状态为 merged，
        # 当所有子申请都已上传报销凭证时，再推动父申请进入已报销。
        if purchase_request.parent_request_id:
            parent_request = purchase_request.parent_request
            if parent_request:
                has_unreimbursed = parent_request.merged_children.filter(
                    reimbursement_details__isnull=True
                ).exists()
                if not has_unreimbursed and parent_request.status != 'reimbursed':
                    parent_request.status = 'reimbursed'
                    parent_request.save(update_fields=['status'])
            return

        purchase_request.status = 'reimbursed'
        purchase_request.save(update_fields=['status'])  # 仅更新 status 字段

    def get_queryset(self):
        """
        （可选）如果需要，可以限制用户只能看到与其相关的报销。
        目前，我们只开放了创建功能，list/retrieve 功能暂未在前端使用。
        """
        return super().get_queryset()

# --- 【新】代码结束 ---
