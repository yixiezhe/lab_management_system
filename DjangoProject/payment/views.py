# payment/views.py
from rest_framework import viewsets, mixins, status, views # <-- 【修改点 1】导入 'views'
from rest_framework.response import Response
from django.shortcuts import get_object_or_404 # <-- 【修改点 2】导入 get_object_or_404
from .models import Payment
from procurement.models import PurchaseRequest # <-- 【修改点 3】导入 PurchaseRequest 模型
from .serializers import PaymentSerializer
from procurement.permissions import IsPayer


class PaymentViewSet(mixins.CreateModelMixin,
                     mixins.RetrieveModelMixin,
                     mixins.UpdateModelMixin,
                     viewsets.GenericViewSet):
    """
    处理支付记录的创建和更新。
    - create: 创建一个新的支付记录（上传截图）
    - retrieve: 查看某个支付记录的详情
    - update/partial_update: 更新支付记录（例如，更换截图）
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsPayer]  # 只有付款人才能访问

    def perform_create(self, serializer):
        # 创建支付记录时，执行额外的动作

        # 1. 将当前登录用户设为支付人
        payment_instance = serializer.save(paid_by=self.request.user)

        # 2. 找到关联的采购申请，并将其状态更新为“已支付”
        purchase_request = payment_instance.purchase_request
        if purchase_request.status == 'approved':
            purchase_request.status = 'paid'
            purchase_request.save()
        else:
            # 如果采购申请不是“已批准”状态，可能是一个异常情况
            # 这里可以抛出异常或记录日志
            # 为简单起见，我们暂时只打印一条警告
            print(f"Warning: Payment recorded for request {purchase_request.id} which is not in 'approved' status.")


# --- 【修改点 4】新增一个 API 视图，专门用于处理付款驳回的逻辑 ---
class RejectPurchaseRequestAPIView(views.APIView):
    """
    一个专门用于付款人驳回采购申请的 API 视图。
    """
    permission_classes = [IsPayer]

    def post(self, request, pk, format=None):
        # 根据传入的 pk (primary key) 获取采购申请实例
        purchase_request = get_object_or_404(PurchaseRequest, pk=pk)

        # 安全检查：确保只有“已批准”状态的申请才能被付款人驳回
        if purchase_request.status != 'approved':
            return Response(
                {'error': f'该申请当前状态为“{purchase_request.get_status_display()}”，无法执行驳回操作。'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 从请求体中获取驳回原因
        reason = request.data.get('reason', '').strip()
        if not reason:
            return Response(
                {'error': '必须提供驳回原因。'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新采购申请的状态和驳回原因
        purchase_request.status = 'payment_rejected'
        # 我们给驳回原因加上前缀，以便审批人能区分是自己驳回的还是付款人驳回的
        purchase_request.rejection_reason = f"付款驳回: {reason}"
        purchase_request.save(update_fields=['status', 'rejection_reason'])

        return Response(
            {'status': '申请已成功驳回，并退回至采购审批环节。'},
            status=status.HTTP_200_OK
        )