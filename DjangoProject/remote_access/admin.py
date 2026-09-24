from django.contrib import admin
from django import forms
# 1. 移除了 RdpAccount 的导入
from .models import RdpMachine, RdpBooking


class RdpMachineAdminForm(forms.ModelForm):
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        help_text="Windows 登录密码（仅用于加密保存，不会明文显示）"
    )
    device_secret = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=True),
        help_text="设备自动登录密钥（会显示已保存的值，注意安全）"
    )

    class Meta:
        model = RdpMachine
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                if self.instance.encrypted_device_secret:
                    # 回显设备密钥（按你的要求显示保存值）
                    self.fields["device_secret"].initial = self.instance.device_secret
            except Exception:
                pass

    def save(self, commit=True):
        obj = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")
        raw_secret = self.cleaned_data.get("device_secret")
        if raw_password:
            obj.password = raw_password
        if raw_secret is not None:
            obj.set_device_secret(raw_secret)
        if commit:
            obj.save()
        return obj


@admin.register(RdpMachine)
class RdpMachineAdmin(admin.ModelAdmin):
    """
    (已修改) 远程主机管理 (集成了账户)
    """
    form = RdpMachineAdminForm
    # 2. 将 username 添加到列表
    list_display = ('name', 'ip_address', 'username', 'is_active', 'has_device_secret', 'description')
    search_fields = ('name', 'ip_address', 'username')  # 3. 添加 username 到搜索
    list_filter = ('is_active',)
    readonly_fields = ('device_secret_updated_at',)

    # 4. (核心) 将 "username" 和 "password" 添加到编辑字段中
    #    这会使用我们模型中定义的 @property password.setter
    #    在保存时自动加密密码。
    fields = ('name', 'ip_address', 'username', 'password', 'device_secret', 'device_secret_updated_at', 'description', 'is_active')

    def has_device_secret(self, obj):
        return bool(obj.device_secret_hash or obj.encrypted_device_secret)
    has_device_secret.boolean = True
    has_device_secret.short_description = "设备密钥已设置"

    # (注意) 'password' 字段只会显示一个输入框，
    # 它不会显示已保存的密码（这是为了安全），这在 Admin 中是正常行为。
    # 每次保存时，输入框中的内容（如果是空白）不会覆盖已有的加密密码。
    # (如果需要修改密码，在输入框中输入新密码即可)


# 5. RdpAccountAdmin 类已被完全删除


@admin.register(RdpBooking)
class RdpBookingAdmin(admin.ModelAdmin):
    """
    (已修改) 远程预约记录管理
    """
    # 6. 将 'account' 替换为 'machine'
    list_display = ('user', 'machine', 'start_time', 'end_time', 'status')
    search_fields = ('user__username', 'machine__name', 'machine__username')
    list_filter = ('status', 'start_time', 'machine')
    date_hierarchy = 'start_time'

    # 7. 将 'account' 替换为 'machine'
    readonly_fields = ('user', 'machine', 'start_time', 'end_time')

    def get_fields(self, request, obj=None):
        # 8. 将 'account' 替换为 'machine'
        if obj:  # 编辑时
            return ('user', 'machine', 'start_time', 'end_time', 'status')
        else:  # 创建时
            return ('user', 'machine', 'start_time', 'end_time', 'status')
