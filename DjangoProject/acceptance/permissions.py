from rest_framework import permissions
from procurement.models import PurchaseRequest
from procurement.permissions import IsApprover


class CanSubmitAcceptancePermission(permissions.BasePermission):
    """
    自定义权限，用于处理验收信息的提交：
    - 允许 '审批人' 角色执行所有操作 (list, retrieve, update, destroy)。
    - 允许普通用户为自己名下 '已支付' 状态的申请创建 (create) 验收记录。
    """

    def has_permission(self, request, view):
        # 首先，确保用户已登录
        if not request.user or not request.user.is_authenticated:
            return False

        # 如果用户是审批人，则允许所有操作
        if IsApprover().has_permission(request, view):
            return True

        # 对于非审批人用户，只允许他们执行 'create' 操作
        if view.action == 'create':
            purchase_request_id = request.data.get('purchase_request')
            if not purchase_request_id:
                return False  # 如果请求体中没有提供 purchase_request ID，则拒绝

            try:
                # 获取关联的采购申请
                purchase_request = PurchaseRequest.objects.get(pk=purchase_request_id)

                # 检查：
                # 1. 当前用户是否为该申请的申请人
                # 2. 该申请的状态是否为 'paid' (已支付)
                # 3. 该申请是否还没有验收记录
                is_owner = purchase_request.applicant == request.user
                is_paid = purchase_request.status == 'paid'
                not_yet_accepted = not hasattr(purchase_request, 'acceptance')

                return is_owner and is_paid and not_yet_accepted

            except PurchaseRequest.DoesNotExist:
                return False  # 如果采购申请不存在，则拒绝

        # 对于非审批人的其他所有操作 (如 list, update 等) 都拒绝
        return False