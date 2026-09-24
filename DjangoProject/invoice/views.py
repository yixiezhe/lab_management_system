from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from .models import Invoice
from common_serializers.serializers import InvoiceSerializer
from procurement.models import PurchaseRequest
from procurement.permissions import IsApprover


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    处理发票信息的创建、查看、更新。
    使用 ModelViewSet 以支持 PATCH 等标准方法。
    """
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated, IsApprover]

    def perform_create(self, serializer):
        """
        重写 perform_create 以处理状态检查和转换。
        """
        purchase_request = serializer.validated_data.get('purchase_request')

        # 状态校验逻辑保持不变
        allowed_statuses = ['goods_received', 'invoiced', 'accepted', 'inspection_skipped']
        if purchase_request.status not in allowed_statuses:
            raise serializers.ValidationError(
                f"此申请的状态为'{purchase_request.get_status_display()}'，无法提交发票。"
            )

        # 【核心修改】直接调用 save()，不再需要手动传入 submitted_by
        serializer.save()

    def perform_update(self, serializer):
        """
        重写 perform_update 以处理更新逻辑。
        """
        purchase_request = serializer.instance.purchase_request

        # 状态校验逻辑保持不变
        allowed_statuses = ['goods_received', 'invoiced', 'accepted', 'inspection_skipped']
        if purchase_request.status not in allowed_statuses:
            raise serializers.ValidationError(
                f"此申请的状态为'{purchase_request.get_status_display()}'，无法修改发票。"
            )

        # 【核心修改】直接调用 save()，不再需要手动传入 submitted_by
        serializer.save()