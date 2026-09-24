# DjangoProject/contract/serializers.py

from rest_framework import serializers
from .models import Contract


class ContractSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Contract
        # --- MODIFICATION START ---
        # 移除了 'contract_number' 字段
        fields = [
            'id',
            'purchase_request',
            'contract_form',
            'uploaded_at',
            'uploaded_by',
        ]
        read_only_fields = ('uploaded_at',)
        # --- MODIFICATION END ---

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')

        # 1. 将 'contract_form' 重命名为 'contract_file' 以匹配前端期望，并生成完整URL
        if 'contract_form' in representation:
            file_url = representation.pop('contract_form')
            if file_url and request:
                representation['contract_file'] = request.build_absolute_uri(file_url)
            else:
                representation['contract_file'] = None

        # 2. 将 'uploaded_at' 重命名为 'created_at' 以匹配前端期望
        if 'uploaded_at' in representation:
            representation['created_at'] = representation.pop('uploaded_at')

        return representation