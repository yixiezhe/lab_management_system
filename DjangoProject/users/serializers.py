from rest_framework import serializers
from .models import UserProfile, Role
from procurement.models import Platform


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['name']


class TutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['id', 'name', 'team_procurement_enabled']


class UserProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    role_name = serializers.CharField(write_only=True)
    assigned_tutor_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    roles = RoleSerializer(read_only=True, many=True)
    assigned_tutor = TutorSerializer(read_only=True)

    is_c2c_platform_manager = serializers.SerializerMethodField()

    # === 新增：走廊显示屏及Land主机权限字段（给前端用）===
    is_system_admin = serializers.SerializerMethodField()
    is_corridor_screen_manager = serializers.SerializerMethodField()
    is_land_host = serializers.SerializerMethodField()  # 新增
    # ===============================================

    class Meta:
        model = UserProfile
        fields = [
            'id', 'username', 'name', 'email', 'password',
            'role_name', 'assigned_tutor_id', 'roles',
            'assigned_tutor', 'team_procurement_enabled',
            'is_c2c_platform_manager',

            # 新增
            'is_system_admin',
            'is_corridor_screen_manager',
            'is_land_host',  # 新增
        ]
        read_only_fields = [
            'id', 'roles', 'assigned_tutor', 'team_procurement_enabled',
            'is_c2c_platform_manager',
            'is_system_admin', 'is_corridor_screen_manager',
            'is_land_host',  # 新增
        ]

    def get_is_c2c_platform_manager(self, obj):
        """
        检查用户是否是任何 category 为 'c2c' 的平台的负责人。
        `obj` 是正在被序列化的 UserProfile 实例。
        """
        return Platform.objects.filter(managers=obj, category='c2c').exists()

    # === 新增：给前端的权限判断（基于 roles 表）===
    def get_is_system_admin(self, obj):
        # 超级用户直接视为系统管理员
        if getattr(obj, 'is_superuser', False):
            return True
        return obj.roles.filter(name='系统管理员').exists()

    def get_is_corridor_screen_manager(self, obj):
        # 超级用户/系统管理员/走廊显示屏管理人员 都允许进入走廊显示屏管理
        if getattr(obj, 'is_superuser', False):
            return True
        return obj.roles.filter(name__in=['系统管理员', '走廊显示屏管理人员']).exists()

    def get_is_land_host(self, obj):
        # 判断是否是 land设备主机 角色
        return obj.roles.filter(name='land设备主机').exists()
    # ============================

    def validate_role_name(self, value):
        if not Role.objects.filter(name=value).exists():
            raise serializers.ValidationError("指定的角色不存在。")
        return value

    def create(self, validated_data):
        role_name = validated_data.pop('role_name')
        assigned_tutor_id = validated_data.pop('assigned_tutor_id', None)

        user = UserProfile(**validated_data)
        user.set_password(validated_data['password'])
        user.save()

        role = Role.objects.get(name=role_name)
        user.roles.add(role)

        if assigned_tutor_id:
            try:
                tutor = UserProfile.objects.get(id=assigned_tutor_id, roles__name='导师用户')
                user.assigned_tutor = tutor
                user.save()
            except UserProfile.DoesNotExist:
                raise serializers.ValidationError("指定的导师不存在或该用户不是导师。")

        return user