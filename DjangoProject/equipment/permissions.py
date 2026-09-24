from rest_framework.permissions import BasePermission

class IsSystemAdmin(BasePermission):
    """
    判断用户是否具备“系统管理员”角色。
    你的用户模型里 roles.name 包含 '系统管理员' 时放行。
    """
    message = "只有系统管理员可以执行此操作。"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        try:
            return user.roles.filter(name="系统管理员").exists()
        except Exception:
            return False


class IsSystemAdminOrTutor(BasePermission):
    """Allow system administrators and users with the tutor role."""
    message = "只有系统管理员或导师用户可以访问。"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        try:
            return user.roles.filter(name__in=["系统管理员", "导师用户"]).exists()
        except Exception:
            return False
