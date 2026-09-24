from rest_framework import permissions
from procurement.models import Platform


class IsApprover(permissions.BasePermission):
    """
    自定义权限，用于判断用户是否能执行审批相关的操作。
    """

    def has_permission(self, request, view):
        """
        处理页面级权限 (View-level permission)。
        """
        if not (request.user and request.user.is_authenticated):
            return False

        # 检查是否拥有全局审批角色
        user_roles = set(request.user.roles.values_list('name', flat=True))
        approver_roles = {'导师用户', '采购人员', '系统管理员'}
        if not user_roles.isdisjoint(approver_roles):
            return True

        # 如果没有全局角色，再检查是否是任何一个公对公平台的负责人
        if Platform.objects.filter(managers=request.user, category='c2c').exists():
            return True

        return False

    def has_object_permission(self, request, view, obj):
        """
        处理对象级权限 (Object-level permission)。
        `obj` 是当前正在操作的采购申请 (PurchaseRequest) 实例。
        """
        # 检查是否拥有全局审批角色
        user_roles = set(request.user.roles.values_list('name', flat=True))
        approver_roles = {'导师用户', '采购人员', '系统管理员'}
        if not user_roles.isdisjoint(approver_roles):
            return True

        # 如果没有全局角色，检查是否为特定平台的负责人
        if hasattr(obj, 'expense_type') and obj.expense_type == 'c2c' and hasattr(obj, 'platform'):
            return Platform.objects.filter(name=obj.platform, managers=request.user).exists()

        return False


class IsSystemAdmin(permissions.BasePermission):
    """
    自定义权限，只要用户的角色中包含“系统管理员”即可。
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(name='系统管理员').exists()


class CanManageWhitelist(permissions.BasePermission):
    """
    自定义权限，只要用户的角色中包含“系统管理员”或“大总管”即可。
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        user_roles = set(request.user.roles.values_list('name', flat=True))
        required_roles = {'系统管理员', '大总管'}
        return not user_roles.isdisjoint(required_roles)


class LedgerAccessPermission(permissions.BasePermission):
    """
    采购台账权限控制:
    - 系统管理员: 拥有所有权限 (读写)。
    - 付款人, 大总管, 采购人员, 导师用户: 仅拥有只读权限。
    - 其他角色: 无权访问。
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        user_roles = set(request.user.roles.values_list('name', flat=True))

        if '系统管理员' in user_roles:
            return True

        read_only_roles = {'付款人', '大总管', '采购人员', '导师用户'}
        if not user_roles.isdisjoint(read_only_roles):
            return request.method in permissions.SAFE_METHODS

        return False


class IsOwnerAndStatusEditable(permissions.BasePermission):
    """
    对象级权限：
    允许用户修改自己的采购申请，但仅当申请状态为“待审批”或“已驳回”时。
    """

    def has_object_permission(self, request, view, obj):
        return obj.applicant == request.user and obj.status in ['pending', 'rejected']


class IsPayer(permissions.BasePermission):
    """
    自定义权限，只要用户的角色中包含“付款人”即可。
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(name='付款人').exists()


class CanApproveTeamRequest(permissions.BasePermission):
    """
    对象级权限：检查用户是否有权审批某个特定的小组请购。
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not obj.tutor:
            return False
        if user == obj.tutor:
            return True
        user_roles = set(user.roles.values_list('name', flat=True))
        if '小组采购人员' in user_roles and user.assigned_tutor == obj.tutor:
            return True
        return False


class IsOwnerAndPending(permissions.BasePermission):
    """
    对象级权限：
    允许用户操作自己的采购申请，但仅当申请状态为“待审批”时。
    """

    def has_object_permission(self, request, view, obj):
        return obj.applicant == request.user and obj.status == 'pending'


class IsTutor(permissions.BasePermission):
    """
    自定义权限，只要用户的角色中包含“导师用户”即可。
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(name='导师用户').exists()


class IsOwnerAndReadyForAcceptance(permissions.BasePermission):
    """
    对象级权限: 仅当满足以下所有条件时，才允许用户提交收货信息：
    1. 用户是该申请的申请人。
    2. 该申请的状态是 'paid' (待收货)。
    """
    message = '只有申请人才能在申请被支付后提交收货信息。'

    def has_object_permission(self, request, view, obj):
        return (
                obj.applicant == request.user and
                obj.status == 'paid'
        )


class IsChiefSteward(permissions.BasePermission):
    """
    自定义权限，只要用户的角色中包含“大总管”即可。
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(name='大总管').exists()

# --- 【新功能】 ---
class IsProjectAdmin(permissions.BasePermission):
    """
    自定义权限，只要用户的角色中包含“项目管理员”即可。
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.roles.filter(name='项目管理员').exists()
# --- 【新功能结束】 ---


class IsAnnouncementAdmin(permissions.BasePermission):
    """
    公告管理权限：项目管理员、系统管理员或超级用户可发布和修改公告。
    """
    message = '只有管理员可以管理公告。'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if getattr(request.user, 'is_superuser', False):
            return True
        if getattr(request.user, 'is_system_admin', False):
            return True
        return request.user.roles.filter(name='项目管理员').exists()


class IsNotLandHost(permissions.BasePermission):
    """
    禁止 land 设备主机账号访问普通用户公告阅读能力。
    """
    message = '设备主机账号不能访问公告和反馈。'

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if getattr(request.user, 'is_land_host', False):
            return False
        return not request.user.roles.filter(name='land设备主机').exists()

# procurement/permissions.py
# ... (保留所有现有的 import 和权限类) ...

# --- 【新增权限类】 ---
class CanModifyWhitelist(permissions.BasePermission):
    """
    自定义权限，用于判断用户是否有权修改（增、删、改）白名单项目。
    允许的角色：系统管理员、大总管、导师用户。
    """
    message = '您没有权限修改白名单项目。'  # 可选：自定义错误信息

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        user_roles = set(request.user.roles.values_list('name', flat=True))
        # 定义允许修改的角色集合
        allowed_roles = {'系统管理员', '大总管', '导师用户'}

        # 检查用户角色是否有交集
        return not user_roles.isdisjoint(allowed_roles)

    # 对于白名单，通常不需要对象级权限检查，因为权限是基于角色的，而不是特定项目
    # def has_object_permission(self, request, view, obj):
    #     return self.has_permission(request, view) # 如果需要，可以这样写

# --- 【新增结束】 ---
