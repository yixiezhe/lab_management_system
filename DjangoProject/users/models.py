from django.db import models
from django.contrib.auth.models import AbstractUser


# 角色模型
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="角色名称")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = verbose_name


# 自定义用户模型
class UserProfile(AbstractUser):
    username = models.CharField(max_length=150, unique=True, verbose_name="学号/工号")
    name = models.CharField(max_length=100, verbose_name="姓名")
    email = models.EmailField(max_length=255, verbose_name="邮箱")
    roles = models.ManyToManyField(Role, blank=True, verbose_name="角色")

    assigned_tutor = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
        verbose_name="所属导师",
        limit_choices_to={'roles__name': '导师用户'}
    )

    team_procurement_enabled = models.BooleanField(default=False, verbose_name="启用小组请购")

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['name', 'email']

    def __str__(self):
        return self.name

    # ====== 新增：通用角色判断 + 走廊显示屏管理角色判断 ======
    def has_role(self, role_name: str) -> bool:
        """判断用户是否拥有某个角色（基于 roles ManyToMany）"""
        return self.roles.filter(name=role_name).exists()

    @property
    def is_system_admin(self) -> bool:
        """
        系统管理员判断：
        - Django 超级用户直接视为系统管理员
        - 或者拥有名为“系统管理员”的角色
        """
        return bool(self.is_superuser or self.has_role('系统管理员'))

    @property
    def is_corridor_screen_manager(self) -> bool:
        """
        走廊显示屏管理人员判断：
        - 系统管理员也默认拥有该权限
        - 或者拥有名为“走廊显示屏管理人员”的角色
        """
        return bool(self.is_system_admin or self.has_role('走廊显示屏管理人员'))

    @property
    def is_land_host(self) -> bool:
        """
        land设备主机角色判断：
        - 拥有名为“land设备主机”的角色
        """
        return self.has_role('land设备主机')
    # ======================================================

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = verbose_name


# --- START OF MODIFICATION ---
class PasswordResetRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已批准'),
        ('rejected', '已驳回'),
    ]

    user = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        verbose_name="申请用户"
    )
    new_password_hash = models.CharField(max_length=128, verbose_name="加密后的新密码")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="申请状态",
        db_index=True
    )
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="申请时间")
    approved_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_password_resets',
        verbose_name="审核人"
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")

    def __str__(self):
        return f"{self.user.name} ({self.user.username}) 的密码重置申请"

    class Meta:
        verbose_name = "密码重置申请"
        verbose_name_plural = verbose_name
        ordering = ['-requested_at']
# --- END OF MODIFICATION ---