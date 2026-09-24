from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Inspection
from .serializers import InspectionSerializer
from procurement.models import PurchaseRequest
from procurement.permissions import IsApprover


class InspectionViewSet(viewsets.ModelViewSet):
    queryset = Inspection.objects.all()
    serializer_class = InspectionSerializer
    permission_classes = [IsAuthenticated, IsApprover]

    def perform_create(self, serializer):
        """
        重写 perform_create 方法以实现自定义逻辑
        """
        # 从序列化器的验证数据中获取 purchase_request 实例
        # 相比从 request.data 获取ID再查询，这样更安全、更高效
        purchase_request = serializer.validated_data.get('purchase_request')

        # 【核心修改】根据新流程，检查状态是否为 'invoiced' (已开票/待验收)
        if purchase_request.status != 'invoiced':
            raise serializers.ValidationError(
                f"此采购申请的状态为'{purchase_request.get_status_display()}'，无法提交验收信息。"
            )

        # 保存验收信息，并将验收人设为当前用户
        serializer.save(inspector=self.request.user)

        # 更新采购申请的状态为 'accepted' (已验收 -> 在新流程中意味着'待报销')
        purchase_request.status = 'accepted'
        purchase_request.save(update_fields=['status'])