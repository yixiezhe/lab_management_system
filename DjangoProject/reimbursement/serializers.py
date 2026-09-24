from rest_framework import serializers
# --- 【新】导入 Reimbursement 模型 ---
from .models import PublicExpenseRecord, C2CExpenseRecord, Reimbursement
from procurement.models import PurchaseRequest


# --- END ---

class PublicExpenseRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicExpenseRecord
        fields = '__all__'


class C2CExpenseRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = C2CExpenseRecord
        fields = '__all__'


# --- 【新】为 Reimbursement 模型创建 Serializer ---
class ReimbursementSerializer(serializers.ModelSerializer):
    """
    报销凭证的序列化器，用于创建新的报销记录。
    """

    # 允许前端通过 ID 关联到 PurchaseRequest
    purchase_request = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseRequest.objects.all(),
        write_only=True
    )

    class Meta:
        model = Reimbursement
        fields = [
            'id',
            'purchase_request',
            'reimbursement_number',
            'actual_amount',
            'reimbursement_photo',
            'submitted_by',
            'created_at',
        ]
        read_only_fields = ('id', 'submitted_by', 'created_at')

# --- 【新】代码结束 ---
