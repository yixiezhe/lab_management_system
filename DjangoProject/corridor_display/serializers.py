from rest_framework import serializers
from .models import DisplayImage, DisplayConfig

class DisplayImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = DisplayImage
        fields = [
            'id', 'name', 'url',
            'width', 'height',
            'order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'url', 'width', 'height', 'created_at', 'updated_at']

    def get_url(self, obj):
        if not obj.image:
            return ''
        # ✅ 修改：强制返回相对路径（如 /media/xxx.jpg）
        # 让前端根据当前访问的域名自动拼接 host，解决跨域和 IP 变动导致的图片不显示问题
        return obj.image.url


class DisplayImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = DisplayImage
        fields = ['id', 'image', 'name', 'order']
        read_only_fields = ['id', 'order']


class DisplayConfigSerializer(serializers.ModelSerializer):
    duty_text = serializers.CharField(required=False, allow_blank=True, trim_whitespace=False)

    class Meta:
        model = DisplayConfig
        fields = [
            'carousel_interval_ms',
            'state',
            'tip',
            'safety',
            'notes',
            'duty_text',
            'duty_week1_start',
            'duty_rotation_unit',
            'package_duty_list',
            'lab_duty_groups',
            'updated_at',
        ]
        read_only_fields = ['updated_at']

    def validate_notes(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("notes 必须是字符串数组。")
        for x in value:
            if not isinstance(x, str):
                raise serializers.ValidationError("notes 必须是字符串数组。")
        return value

    def validate_package_duty_list(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("package_duty_list 必须是字符串数组。")

        cleaned = [str(x).strip() for x in value if str(x).strip()]
        return cleaned

    def validate_lab_duty_groups(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("lab_duty_groups 必须是字符串数组。")

        cleaned = [str(x).strip() for x in value if str(x).strip()]
        return cleaned
