from rest_framework import serializers
from .models import Project
from users.serializers import UserProfileSerializer

class ProjectSerializer(serializers.ModelSerializer):
    """
    项目模型的序列化器
    """
    # 使用嵌套序列化器，在API中直接显示作者的详细信息
    author = UserProfileSerializer(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'project_number',
            'name',
            'description',
            # 'is_published', # 【已移除】
            'author',

            'created_at',
            'updated_at'
        ]
        read_only_fields = ('author', 'created_at', 'updated_at')