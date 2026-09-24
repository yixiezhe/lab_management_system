from rest_framework import serializers
from .models import AnnouncementRead, WhitelistItem, Platform, GlobalAnnouncement, PublicProcurementDutySchedule
from users.models import UserProfile
from users.serializers import UserProfileSerializer


# ==========================================================================
# procurement app 现在只保留自己特有的、不被其他app直接依赖的序列化器
# ==========================================================================

class WhitelistItemSerializer(serializers.ModelSerializer):
    """
    白名单项目的序列化器。
    """
    main_category = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    # --- 【新】显式定义 platform 字段，使其非必填 ---
    platform = serializers.CharField(required=False, allow_blank=True)
    # --- END ---

    class Meta:
        model = WhitelistItem
        fields = '__all__'


class PlatformSerializer(serializers.ModelSerializer):
    """
    采购平台模型的序列化器。
    """
    managers_details = UserProfileSerializer(source='managers', many=True, read_only=True)
    managers = serializers.PrimaryKeyRelatedField(
        queryset=UserProfile.objects.all(),
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Platform
        fields = [
            'id',
            'name',
            'prefix',
            'category',
            'managers',  # 只写
            'managers_details'  # 只读
        ]

    def validate_prefix(self, value):
        """
        验证单号前缀
        """
        if not value:
            return value

        if len(value) != 1 or not value.isalpha() or not value.isupper():
            raise serializers.ValidationError("单号前缀必须是单个大写英文字母。")

        return value

    # --- 【最终修复：新增 create 和 update 方法】 ---
    def create(self, validated_data):
        """
        自定义创建方法，以正确处理 managers 多对多关系。
        """
        # 1. 先将 managers 数据从验证过的数据中弹出
        managers_data = validated_data.pop('managers', [])
        # 2. 创建不包含 managers 的平台实例
        platform = Platform.objects.create(**validated_data)
        # 3. 为新创建的平台设置 managers
        if managers_data:
            platform.managers.set(managers_data)
        return platform

    def update(self, instance, validated_data):
        """
        自定义更新方法，以正确处理 managers 多对多关系。
        """
        # 1. 先将 managers 数据从验证过的数据中弹出
        managers_data = validated_data.pop('managers', None)
        # 2. 调用父类方法，更新平台的常规字段 (name, prefix 等)
        instance = super().update(instance, validated_data)

        # 3. 如果请求中包含了 managers 数据，则更新多对多关系
        #    如果请求中没带 managers 字段, managers_data 会是 None, 不会执行清空操作
        if managers_data is not None:
            instance.managers.set(managers_data)

        return instance
    # --- 【最终修复结束】 ---


class GlobalAnnouncementSerializer(serializers.ModelSerializer):
    """
    公告序列化器。
    """
    created_by = UserProfileSerializer(read_only=True)
    updated_by = UserProfileSerializer(read_only=True)
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = GlobalAnnouncement
        fields = [
            'id',
            'title',
            'content',
            'is_published',
            'show_popup',
            'created_by',
            'created_at',
            'updated_by',
            'updated_at',
            'is_read',
        ]
        read_only_fields = ('created_by', 'created_at', 'updated_at', 'updated_by', 'is_read')

    def get_is_read(self, obj):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return AnnouncementRead.objects.filter(
            announcement=obj,
            user=user,
            read_at__gte=obj.updated_at,
        ).exists()

    def validate_title(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('请填写公告标题。')
        return value

    def validate_content(self, value):
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('请填写公告内容。')
        return value

class PublicProcurementDutyScheduleSerializer(serializers.ModelSerializer):
    """
    公共经费采购流程每周采购人设置序列化器。
    """
    updated_by = UserProfileSerializer(read_only=True)

    class Meta:
        model = PublicProcurementDutySchedule
        fields = '__all__'
        read_only_fields = ('updated_at', 'updated_by')

    def validate_weekly_duty(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('weekly_duty 必须是数组。')

        seen_weekdays = set()
        weekday_to_name = {i: '' for i in range(7)}

        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f'第 {idx + 1} 项必须是对象。')

            weekday = item.get('weekday')
            try:
                weekday = int(weekday)
            except (TypeError, ValueError):
                raise serializers.ValidationError(f'第 {idx + 1} 项的 weekday 必须是 0-6 的整数。')

            if weekday < 0 or weekday > 6:
                raise serializers.ValidationError(f'第 {idx + 1} 项的 weekday 超出范围（0-6）。')

            if weekday in seen_weekdays:
                raise serializers.ValidationError(f'weekday={weekday} 重复，请保证每个星期只出现一次。')
            seen_weekdays.add(weekday)

            raw_name = item.get('name', '')
            if raw_name is None:
                raw_name = ''
            if not isinstance(raw_name, str):
                raise serializers.ValidationError(f'第 {idx + 1} 项的 name 必须是字符串。')

            weekday_to_name[weekday] = raw_name.strip()

        return [{'weekday': i, 'name': weekday_to_name[i]} for i in range(7)]
