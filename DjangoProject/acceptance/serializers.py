# acceptance/serializers.py
from rest_framework import serializers
from .models import Acceptance
from procurement.models import PurchaseRequest

class AcceptanceSerializer(serializers.ModelSerializer):
    # 【核心修改】我们在此处明确定义 purchase_request 字段。
    # DRF默认会为 OneToOneField 自动添加唯一性验证 (UniqueValidator)。
    # 通过显式定义，我们可以绕过这个默认验证，将“是否已存在”的逻辑完全交由 view 中的 update_or_create 处理。
    purchase_request = serializers.PrimaryKeyRelatedField(
        queryset=PurchaseRequest.objects.all(),
        label="关联的采购申请"
    )

    class Meta:
        model = Acceptance
        fields = [
            'id', 'purchase_request', 'receiving_status',
            'acceptance_photo', 'recorded_by', 'created_at', 'updated_at'
        ]
        read_only_fields = ('recorded_by', 'created_at', 'updated_at')