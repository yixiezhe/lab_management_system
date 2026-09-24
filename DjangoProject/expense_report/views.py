from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from .models import ExpenseReport
from .serializers import ExpenseReportSerializer
from procurement.models import PurchaseRequest
from procurement.permissions import IsApprover


class ExpenseReportViewSet(viewsets.ModelViewSet):
    queryset = ExpenseReport.objects.all()
    serializer_class = ExpenseReportSerializer
    permission_classes = [IsAuthenticated, IsApprover]

    def perform_create(self, serializer):
        # 从序列化器的验证数据中获取 purchase_request 实例
        purchase_request = serializer.validated_data.get('purchase_request')

        # 【核心修改】根据新流程，允许在 'accepted' 或 'inspection_skipped' 状态下提交报销单
        allowed_statuses = ['accepted', 'inspection_skipped']
        if purchase_request.status not in allowed_statuses:
            raise serializers.ValidationError(
                f"此采购申请的状态为'{purchase_request.get_status_display()}'，无法提交报销单。"
            )

        # 保存报销单实例，并设置提交者
        serializer.save(submitted_by=self.request.user)

        # 提交报销单后，将总流程状态更新为 'reimbursed' (已报销)
        purchase_request.status = 'reimbursed'
        purchase_request.save(update_fields=['status'])