from rest_framework.permissions import BasePermission


class IsNotLandHost(BasePermission):
    message = "land 设备主机账号不能访问公告和反馈。"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_land_host", False):
            return False

        try:
            return not user.roles.filter(name="land设备主机").exists()
        except Exception:
            return True


class IsSystemAdmin(BasePermission):
    message = "只有系统管理员可以回复反馈。"

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True
        if getattr(user, "is_system_admin", False):
            return True

        try:
            return user.roles.filter(name="系统管理员").exists()
        except Exception:
            return False
