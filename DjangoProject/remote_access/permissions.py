# remote_access/permissions.py
from rest_framework import permissions


def check_is_system_admin(user):
    """
    辅助函数：检查用户是否具有 '系统管理员' 角色。

    (基于 authStore.js 和 users/models.py 的 README 文档,
     我们假设 UserProfile 与 Role 是多对多关系,
     且 Role 模型有一个 'name' 字段)
    """
    if not user or not user.is_authenticated:
        return False

    # (核心修正) 检查用户的 "roles" (多对多) 中是否存在一个 "name" 为 "系统管理员" 的角色
    try:
        # --- 修正：从 'System Admin' 改为 '系统管理员' ---
        return user.roles.filter(name='系统管理员').exists()
    except AttributeError:
        # 如果 'roles' 关系不存在或名称不符，则返回 False，防止崩溃
        return False


class IsSystemAdmin(permissions.BasePermission):
    """
    自定义权限：只允许系统管理员 (角色为 '系统管理员') 访问。
    """

    def has_permission(self, request, view):
        # 检查用户是否已登录并且是系统管理员
        return check_is_system_admin(request.user)


class IsSystemAdminOrReadOnly(permissions.BasePermission):
    """
    自定义权限：允许任何人 (已登录) 进行 "安全" 操作 (GET, HEAD, OPTIONS)，
    但只允许系统管理员进行 "写入" 操作 (POST, PUT, PATCH, DELETE)。
    """

    def has_permission(self, request, view):
        # 对所有人（已登录）开放 Read-Only 请求
        if request.method in permissions.SAFE_METHODS:
            return request.user and request.user.is_authenticated

        # 否则，只允许系统管理员进行写入操作
        return check_is_system_admin(request.user)