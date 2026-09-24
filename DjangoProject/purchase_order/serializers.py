# DjangoProject/purchase_order/serializers.py

from rest_framework import serializers
from .models import PurchaseOrder


class PurchaseOrderSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = PurchaseOrder
        fields = '__all__'
        read_only_fields = ('uploaded_at',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')

        # --- MODIFICATION START ---
        # 1. 将 'po_form' 重命名为 'order_file' 以匹配前端期望，并生成完整URL
        if 'po_form' in representation:
            file_url = representation.pop('po_form')
            if file_url and request:
                representation['order_file'] = request.build_absolute_uri(file_url)
            else:
                representation['order_file'] = None

        # 2. 将 'uploaded_at' 重命名为 'created_at' 以匹配前端期望
        if 'uploaded_at' in representation:
            representation['created_at'] = representation.pop('uploaded_at')
        # --- MODIFICATION END ---

        return representation