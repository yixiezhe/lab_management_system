from rest_framework import serializers
from .models import Inspection


class InspectionSerializer(serializers.ModelSerializer):
    # 让 inspector 字段在返回时显示用户名，而不是用户ID
    inspector_name = serializers.CharField(source='inspector.name', read_only=True)

    class Meta:
        model = Inspection
        # 显式列出字段，方便管理，并将 inspector_name 添加进来
        fields = [
            'id', 'purchase_request', 'inspection_number', 'inspection_photo',
            'inspector', 'inspector_name', 'inspected_at'
        ]
        read_only_fields = ('inspector', 'inspected_at', 'inspector_name')

    def to_representation(self, instance):
        """
        【核心修改】重写此方法，以构建 inspection_photo 的完整URL。
        """
        # 首先，调用父类的方法获取标准的序列化数据（字典格式）
        representation = super().to_representation(instance)

        # 从 serializer 的上下文中获取当前的 request 对象
        request = self.context.get('request')

        # 检查 'inspection_photo' 字段是否有值，并且 request 对象存在
        if representation.get('inspection_photo') and request:
            # 使用 request.build_absolute_uri 方法将相对路径转换为绝对URL
            representation['inspection_photo'] = request.build_absolute_uri(
                representation['inspection_photo']
            )

        return representation