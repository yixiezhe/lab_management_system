from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone
from .models import Role, UserProfile, PasswordResetRequest


# 创建一个自定义的 UserAdmin 类
class UserProfileAdmin(UserAdmin):
    list_display = ('username', 'name', 'display_roles', 'is_staff', 'is_active')
    list_editable = ('is_staff', 'is_active')
    list_filter = ('roles', 'is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('name', 'email')}),
        ('Permissions', {'fields': (
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions',
            'roles', 'assigned_tutor'
        )}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    def display_roles(self, obj):
        """在后台列表页显示用户的多个角色，以逗号分隔"""
        return ", ".join([role.name for role in obj.roles.all()])

    display_roles.short_description = '角色'


# 注册 Role 模型
admin.site.register(Role)
# 使用我们自定义的 UserProfileAdmin 来注册 UserProfile
admin.site.register(UserProfile, UserProfileAdmin)


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'requested_at', 'approved_by', 'approved_at')
    list_filter = ('status',)
    # 【修改点】将 status 加入 list_editable，方便在列表页直接修改状态
    list_editable = ('status',)
    readonly_fields = ('user', 'new_password_hash', 'requested_at', 'approved_by', 'approved_at')
    # 保留 Action 用于批量操作
    actions = ['approve_password_reset']

    def save_model(self, request, obj, form, change):
        """
        重写 save_model 方法，用于处理从编辑页面保存的逻辑。
        `obj` 是正在被保存的 PasswordResetRequest 实例。
        """
        # 检查是否是已存在的对象，并且状态字段被修改了
        if change and 'status' in form.changed_data:
            # 如果新状态是 'approved'
            if obj.status == 'approved':
                user = obj.user
                # 将存储的哈希密码应用到用户对象
                user.password = obj.new_password_hash
                user.save()

                # 更新申请记录的审批人和审批时间
                obj.approved_by = request.user
                obj.approved_at = timezone.now()

                messages.success(request, f"用户 {user.name} 的密码已通过编辑页面成功重置。")

        # 调用父类的 save_model 来完成申请记录自身的保存
        super().save_model(request, obj, form, change)

    @admin.action(description='【批量操作】批准选中的密码重置申请')
    def approve_password_reset(self, request, queryset):
        """
        管理员执行的批量批准操作
        """
        updated_count = 0
        # 只处理状态为 'pending' 的申请
        for reset_request in queryset.filter(status='pending'):
            user = reset_request.user
            user.password = reset_request.new_password_hash
            user.save()

            reset_request.status = 'approved'
            reset_request.approved_by = request.user
            reset_request.approved_at = timezone.now()
            reset_request.save()
            updated_count += 1

        if updated_count > 0:
            self.message_user(request, f"{updated_count} 条密码重置申请已成功批准。", messages.SUCCESS)
        else:
            self.message_user(request, "没有可批准的待审核申请被选中。", messages.WARNING)