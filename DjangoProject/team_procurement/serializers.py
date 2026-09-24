from rest_framework import serializers
from .models import TeamPurchaseRequest, TeamRequestItem
from users.serializers import UserProfileSerializer


class TeamRequestItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeamRequestItem
        # 排除 purchase_request 字段，因为它会由父级自动关联
        exclude = ['purchase_request']


class TeamPurchaseRequestSerializer(serializers.ModelSerializer):
    # 嵌套序列化器，用于在创建/更新时一并处理物品项
    items = TeamRequestItemSerializer(many=True)
    # 只读字段，用于在返回数据时显示详细的用户信息
    applicant = UserProfileSerializer(read_only=True)
    tutor = UserProfileSerializer(read_only=True)
    approved_by = UserProfileSerializer(read_only=True)

    class Meta:
        model = TeamPurchaseRequest
        fields = '__all__'
        # total_price 和 tutor 是后端自动计算的，设为只读
        read_only_fields = ('tutor', 'total_price', 'rejection_reason')

    def create(self, validated_data):
        items_data = validated_data.pop('items')

        # 计算总价
        total_price = sum(
            (item.get('unit_price', 0) * item.get('quantity', 0)) for item in items_data
        )
        validated_data['total_price'] = total_price

        # 创建主申请对象
        purchase_request = TeamPurchaseRequest.objects.create(**validated_data)

        # 批量创建物品项
        for item_data in items_data:
            TeamRequestItem.objects.create(purchase_request=purchase_request, **item_data)

        return purchase_request

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        # 更新主申请对象的字段
        instance = super().update(instance, validated_data)

        # 如果提交的数据中包含 items，则更新物品列表
        if items_data is not None:
            # 先删除旧的 items
            instance.items.all().delete()
            # 重新计算总价并创建新的 items
            total_price = sum(
                (item.get('unit_price', 0) * item.get('quantity', 0)) for item in items_data
            )
            instance.total_price = total_price

            for item_data in items_data:
                TeamRequestItem.objects.create(purchase_request=instance, **item_data)

        instance.save()
        return instance

# --- 【新增点】为小组采购台账创建的专用序列化器 ---
class FullProcessTeamPurchaseRequestSerializer(serializers.ModelSerializer):
    """
    一个只读的序列化器，用于在台账中展示小组采购申请的完整信息。
    """
    items = TeamRequestItemSerializer(many=True, read_only=True)
    applicant = UserProfileSerializer(read_only=True)
    tutor = UserProfileSerializer(read_only=True)
    approved_by = UserProfileSerializer(read_only=True)

    class Meta:
        model = TeamPurchaseRequest
        fields = '__all__'