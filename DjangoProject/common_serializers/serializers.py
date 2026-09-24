from decimal import Decimal

from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from procurement.models import PurchaseRequest, RequestItem
from invoice.models import Invoice
from acceptance.models import Acceptance
from payment.models import Payment
from reimbursement.models import Reimbursement
from users.serializers import UserProfileSerializer
from purchase_order.serializers import PurchaseOrderSerializer
from contract.serializers import ContractSerializer


# ==========================================================================
# 1. 基础组件序列化器
# ==========================================================================

class InvoiceSerializer(serializers.ModelSerializer):
    """发票信息的序列化器"""
    submitted_by = serializers.HiddenField(default=serializers.CurrentUserDefault())
    actual_payment_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.00'),
        required=False,
        write_only=True
    )

    class Meta:
        model = Invoice
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def _update_actual_payment_amount(self, purchase_request, actual_payment_amount):
        if actual_payment_amount is None or purchase_request.expense_type != 'c2c':
            return
        purchase_request.actual_payment_amount = actual_payment_amount
        purchase_request.save(update_fields=['actual_payment_amount'])

    def create(self, validated_data):
        actual_payment_amount = validated_data.pop('actual_payment_amount', None)
        invoice = super().create(validated_data)
        self._update_actual_payment_amount(invoice.purchase_request, actual_payment_amount)
        return invoice

    def update(self, instance, validated_data):
        actual_payment_amount = validated_data.pop('actual_payment_amount', None)
        invoice = super().update(instance, validated_data)
        self._update_actual_payment_amount(invoice.purchase_request, actual_payment_amount)
        return invoice


class AcceptanceSerializer(serializers.ModelSerializer):
    """收货验收信息的序列化器"""
    recorded_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Acceptance
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class PaymentSerializer(serializers.ModelSerializer):
    """支付信息的序列化器"""
    paid_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Payment
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.paid_by:
            representation['paid_by_name'] = instance.paid_by.name
        return representation


class ReimbursementInfoSerializer(serializers.ModelSerializer):
    """报销凭证信息（只读）"""
    class Meta:
        model = Reimbursement
        fields = [
            'id',
            'reimbursement_number',
            'actual_amount',
            'reimbursement_photo',
            'submitted_by',
            'created_at',
        ]
        read_only_fields = fields


class RequestItemSerializer(serializers.ModelSerializer):
    """采购物品的序列化器"""
    # 【最终增强】 添加此字段，以便在前端直接显示每个物品的原始申请人姓名
    original_applicant_name = serializers.CharField(source='original_applicant.name', read_only=True)

    class Meta:
        model = RequestItem
        fields = [
            'id', 'original_applicant', 'original_applicant_name',  # <-- 新增字段
            'purchase_type', 'content', 'manufacturer',
            'parameters', 'cas_number', 'product_number', 'purchase_link',
            'specifications', 'unit_price', 'quantity'
        ]


# ==========================================================================
# 2. 专用的子申请序列化器 (最终版)
# ==========================================================================

class ChildPurchaseRequestSerializer(serializers.ModelSerializer):
    """
    专用于在父申请中序列化子申请信息的、简化的、非递归的序列化器。
    """
    applicant = UserProfileSerializer(read_only=True)
    # 【最终修复】 items字段现在应该是空的（因为物品已移至父申请），但保留以维持结构
    items = RequestItemSerializer(many=True, read_only=True)
    invoice = InvoiceSerializer(read_only=True, allow_null=True, source='latest_invoice')
    invoices = InvoiceSerializer(many=True, read_only=True)
    acceptance = AcceptanceSerializer(read_only=True, allow_null=True)
    payment = PaymentSerializer(read_only=True, allow_null=True)
    reimbursement_details = ReimbursementInfoSerializer(read_only=True)
    purchase_order = PurchaseOrderSerializer(read_only=True)
    contract = ContractSerializer(read_only=True)
    handler = serializers.PrimaryKeyRelatedField(read_only=True)
    handler_name = serializers.CharField(source='handler.name', read_only=True)
    inspection = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequest
        fields = [
            'id', 'order_number', 'request_date', 'platform', 'applicant', 'total_price',
            'actual_payment_amount', 'status',
            'items', 'invoice', 'invoices', 'acceptance', 'payment', 'inspection', 'purchase_order', 'contract',
            'handler', 'handler_name',
            'reimbursement_details'
        ]

    def get_inspection_serializer(self):
        from inspection.serializers import InspectionSerializer
        return InspectionSerializer

    def get_inspection(self, obj):
        InspectionSerializer = self.get_inspection_serializer()
        if hasattr(obj, 'inspection') and obj.inspection:
            return InspectionSerializer(obj.inspection, context=self.context).data
        return None


# ==========================================================================
# 3. “超级序列化器” (台账使用)
# ==========================================================================

class FullProcessPurchaseRequestSerializer(serializers.ModelSerializer):
    """整合采购全流程数据的“超级序列化器”"""
    applicant = UserProfileSerializer(read_only=True)
    applicant_tutor = UserProfileSerializer(read_only=True, source='applicant.assigned_tutor')
    approved_by = UserProfileSerializer(read_only=True)
    handler_name = serializers.SerializerMethodField()
    # 【最终修复】 items现在会由合并逻辑自动填充，此处的定义是正确的
    items = RequestItemSerializer(many=True, read_only=True)
    invoice = InvoiceSerializer(read_only=True, allow_null=True, source='latest_invoice')
    invoices = InvoiceSerializer(many=True, read_only=True)
    acceptance = AcceptanceSerializer(read_only=True, allow_null=True)
    payment = PaymentSerializer(read_only=True, allow_null=True)
    reimbursement_details = ReimbursementInfoSerializer(read_only=True)
    purchase_order = PurchaseOrderSerializer(read_only=True)
    contract = ContractSerializer(read_only=True)
    merged_children = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequest
        fields = [
            'id', 'order_number', 'request_date', 'platform',
            'applicant', 'applicant_tutor', 'approved_by', 'handler', 'handler_name', 'total_price',
            'actual_payment_amount', 'status',
            'items', 'invoice', 'invoices', 'acceptance', 'payment', 'inspection',
            'purchase_order', 'contract', 'merged_children', 'expense_type',
            'reimbursement_details'
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # 仅保留申请人姓名合并的逻辑
        if hasattr(instance, 'merged_children') and instance.merged_children.exists():
            children = instance.merged_children.select_related('applicant').all()
            names = sorted(list({child.applicant.name for child in children if child.applicant}))
            if names and 'applicant' in representation and representation['applicant']:
                display_name = ', '.join(names) + ' (合并)'
                representation['applicant']['name'] = display_name
        return representation

    def get_inspection_serializer(self):
        from inspection.serializers import InspectionSerializer
        return InspectionSerializer

    inspection = serializers.SerializerMethodField()

    def get_inspection(self, obj):
        InspectionSerializer = self.get_inspection_serializer()
        if hasattr(obj, 'inspection') and obj.inspection:
            return InspectionSerializer(obj.inspection, context=self.context).data
        return None

    def get_merged_children(self, obj):
        if hasattr(obj, 'merged_children') and obj.merged_children.exists():
            return ChildPurchaseRequestSerializer(obj.merged_children.all(), many=True, context=self.context).data
        return []

    def get_handler_name(self, obj):
        if getattr(obj, 'handler', None) and getattr(obj.handler, 'name', None):
            return obj.handler.name
        if hasattr(obj, 'merged_children') and obj.merged_children.exists():
            names = sorted({
                child.handler.name
                for child in obj.merged_children.all()
                if getattr(child, 'handler', None) and getattr(child.handler, 'name', None)
            })
            if names:
                return '、'.join(names)
        return None


# ==========================================================================
# 4. 采购申请自身使用的序列化器
# ==========================================================================

class PurchaseRequestSerializer(serializers.ModelSerializer):
    """用于创建和查看单个采购申请的序列化器"""
    items = RequestItemSerializer(many=True)
    applicant = UserProfileSerializer(read_only=True)
    applicant_tutor = UserProfileSerializer(read_only=True, source='applicant.assigned_tutor')
    actual_payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    purchase_order = PurchaseOrderSerializer(read_only=True)
    contract = ContractSerializer(read_only=True)
    acceptance = AcceptanceSerializer(read_only=True, allow_null=True)
    approved_by = UserProfileSerializer(read_only=True)
    handler_name = serializers.SerializerMethodField()
    payment = PaymentSerializer(read_only=True, allow_null=True)
    reimbursement_details = ReimbursementInfoSerializer(read_only=True)
    invoice = InvoiceSerializer(read_only=True, allow_null=True, source='latest_invoice')
    invoices = InvoiceSerializer(many=True, read_only=True)
    inspection = serializers.SerializerMethodField()
    merged_children = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseRequest
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # 仅保留申请人姓名合并的逻辑
        if hasattr(instance, 'merged_children') and instance.merged_children.exists():
            children = instance.merged_children.select_related('applicant').all()
            names = sorted(list({child.applicant.name for child in children if child.applicant}))
            if names and 'applicant' in representation and representation['applicant']:
                display_name = ', '.join(names) + ' (合并)'
                representation['applicant']['name'] = display_name
        return representation

    def get_inspection_serializer(self):
        from inspection.serializers import InspectionSerializer
        return InspectionSerializer

    def get_inspection(self, obj):
        InspectionSerializer = self.get_inspection_serializer()
        if hasattr(obj, 'inspection') and obj.inspection:
            return InspectionSerializer(obj.inspection, context=self.context).data
        return None

    def get_merged_children(self, obj):
        if hasattr(obj, 'merged_children') and obj.merged_children.exists():
            return ChildPurchaseRequestSerializer(obj.merged_children.all(), many=True, context=self.context).data
        return []

    def get_handler_name(self, obj):
        if getattr(obj, 'handler', None) and getattr(obj.handler, 'name', None):
            return obj.handler.name
        if hasattr(obj, 'merged_children') and obj.merged_children.exists():
            names = sorted({
                child.handler.name
                for child in obj.merged_children.all()
                if getattr(child, 'handler', None) and getattr(child.handler, 'name', None)
            })
            if names:
                return '、'.join(names)
        return None

    def validate(self, data):
        expense_type = data.get('expense_type')
        items_data = data.get('items')

        if expense_type == 'public':
            if not items_data:
                raise ValidationError("公共经费申请必须至少包含一个采购物品。")

            for index, item_data in enumerate(items_data):
                link = item_data.get('purchase_link')
                if not link or not link.strip():
                    error_detail = f"物品 {index + 1} ({item_data.get('content', '未知')})：必须提供采购链接。"
                    raise ValidationError({"items": error_detail})
        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        purchase_request = PurchaseRequest.objects.create(**validated_data)
        for item_data in items_data:
            # 修复核心：如果前端传了 original_applicant，先移除，避免与后面显式传参冲突
            item_data.pop('original_applicant', None)

            RequestItem.objects.create(
                purchase_request=purchase_request,
                original_applicant=purchase_request.applicant,
                **item_data
            )
        return purchase_request

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        instance = super().update(instance, validated_data)

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                # 修复核心：如果前端传了 original_applicant，先移除，避免与后面显式传参冲突
                item_data.pop('original_applicant', None)

                RequestItem.objects.create(
                    purchase_request=instance,
                    original_applicant=instance.applicant,
                    **item_data
                )
        return instance
