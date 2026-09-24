# DjangoProject/contract/views.py

from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from .models import Contract
from .serializers import ContractSerializer
from procurement.permissions import IsApprover

class ContractViewSet(viewsets.ModelViewSet):
    queryset = Contract.objects.all()
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated, IsApprover]

    def perform_create(self, serializer):
        purchase_request = serializer.validated_data.get('purchase_request')
        if purchase_request.status != 'pending_contract':
            raise serializers.ValidationError(
                f"此申请的状态为'{purchase_request.get_status_display()}'，无法上传合同。"
            )
        serializer.save()