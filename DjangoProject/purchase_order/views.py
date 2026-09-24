# DjangoProject/purchase_order/views.py

from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from .models import PurchaseOrder
from .serializers import PurchaseOrderSerializer
from procurement.permissions import IsApprover

class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated, IsApprover]

    def perform_create(self, serializer):
        purchase_request = serializer.validated_data.get('purchase_request')
        if purchase_request.status != 'pending_purchase_order':
            raise serializers.ValidationError(
                f"此申请的状态为'{purchase_request.get_status_display()}'，无法上传请购单。"
            )
        serializer.save()