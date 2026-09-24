# team_procurement/permissions.py

from rest_framework import permissions


class CanApproveTeamRequest(permissions.BasePermission):
    """
    自定义权限，允许导师或其指定的小组采购人员审批组内申请。
    """
    message = '您没有权限审批此申请。'

    def has_object_permission(self, request, view, obj):
        # obj 是 TeamPurchaseRequest 实例
        user = request.user
        tutor = obj.tutor

        # 如果申请没有导师，则拒绝 (理论上不应发生)
        if not tutor:
            return False

        # 1. 申请人所属的导师可以直接审批
        if user == tutor:
            return True

        # 2. 如果当前用户是小组采购人员，并且是该导师小组的成员
        user_roles = set(user.roles.values_list('name', flat=True))
        if '小组采购人员' in user_roles and user.assigned_tutor == tutor:
            return True

        return False


# --- 【新增点】为小组台账创建的权限 ---
class TeamLedgerAccessPermission(permissions.BasePermission):
    """
    自定义权限，允许导师、其小组采购人员及系统管理员访问小组台账。
    """
    message = '您没有权限访问小组台账。'

    def has_permission(self, request, view):
        # 뷰셋의 get_queryset에서 실제 데이터 필터링이 이루어지므로,
        # 여기서는 단순히 특정 역할을 가진 사용자가 이 뷰에 접근할 수 있는지 여부만 확인합니다.
        # 실제 데이터 필터링(데이터 격리)은 뷰셋의 get_queryset에서 처리됩니다.

        if not request.user or not request.user.is_authenticated:
            return False

        user_roles = set(request.user.roles.values_list('name', flat=True))

        # 系统管理员可以访问
        if '系统管理员' in user_roles:
            return True

        # 导师可以访问
        if '导师用户' in user_roles:
            return True

        # 小组采购人员可以访问
        if '小组采购人员' in user_roles:
            return True

        # 其他所有角色都不能访问
        return False