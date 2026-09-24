# payment/serializers.py
from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'
        # paid_by 字段将从请求的用户中自动填充，设为只读
        read_only_fields = ('paid_by',)