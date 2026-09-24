from rest_framework.permissions import BasePermission


class IsSystemAdmin(BasePermission):
    message = "只有系统管理员可以使用智能助手。"

    def has_permission(self, request, view):
        user = request.user
        if not user or not getattr(user, "is_authenticated", False):
            return False
        return bool(
            getattr(user, "is_superuser", False)
            or getattr(user, "is_system_admin", False)
        )
