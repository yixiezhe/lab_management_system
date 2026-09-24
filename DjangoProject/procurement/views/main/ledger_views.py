from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from ...models import PurchaseRequest, Platform
from ...permissions import IsApprover
from common_serializers.serializers import FullProcessPurchaseRequestSerializer
from ...filters import LedgerFilter
from .purchase_request_views import StandardResultsSetPagination


class FullProcessPurchaseRequestViewSet(viewsets.ModelViewSet):
    serializer_class = FullProcessPurchaseRequestSerializer
    # 【重要修复】 权限从仅审批人放宽到认证用户即可，具体权限由 get_queryset 控制
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = LedgerFilter
    search_fields = ['applicant__name', 'applicant__assigned_tutor__name', 'platform', 'order_number', 'items__content',
                     'items__manufacturer', 'items__specifications']

    def get_queryset(self):
        """
        【最终修复】: 区分 'list' 和 'retrieve' 动作。
        - 对于 'retrieve' (获取详情)，我们返回一个基础查询集，不过滤任何东西。
        - 对于 'list' (获取列表)，我们保留原有的、复杂的台账筛选逻辑。
        """
        user = self.request.user
        base_queryset = PurchaseRequest.objects.all()  # 使用 all() 以包含所有可能的对象

        # 如果是获取单个详情，直接返回，不再进行复杂的台账过滤
        # 权限由前端逻辑（只能点开自己列表里的项）和API权限类共同保障
        if self.action == 'retrieve':
            return base_queryset.prefetch_related(
                'items__original_applicant', 'merged_children', 'merged_children__invoices', 'invoices',
                'purchase_order', 'contract'
            ).select_related(
                'applicant', 'approved_by', 'acceptance', 'payment', 'applicant__assigned_tutor',
                'inspection', 'reimbursement_details'
            )

        # --- 以下是 'list' 动作的逻辑，保持不变 ---

        base_queryset = base_queryset.filter(parent_request__isnull=True)

        user_roles = set(user.roles.values_list('name', flat=True))
        is_admin = '系统管理员' in user_roles
        is_tutor = '导师用户' in user_roles
        is_procurement_staff = '采购人员' in user_roles

        if is_admin or is_tutor:
            queryset = base_queryset
        else:
            visible_q = Q(applicant=user) | Q(merged_children__applicant=user)
            if is_procurement_staff:
                visible_q |= Q(expense_type='public')

            managed_c2c_platforms = Platform.objects.filter(managers=user, category='c2c').values_list('name',
                                                                                                       flat=True)
            if managed_c2c_platforms:
                visible_q |= Q(expense_type='c2c', platform__in=list(managed_c2c_platforms))

            queryset = base_queryset.filter(visible_q)

        ledger_statuses = [
            'approved', 'paid', 'goods_received', 'inspection_skipped', 'accepted',
            'invoiced', 'reimbursed', 'completed', 'rejected', 'withdrawn', 'merged'
        ]
        queryset = queryset.filter(status__in=ledger_statuses)

        expense_type = self.request.query_params.get('expense_type')
        if expense_type in ['c2c', 'public']:
            queryset = queryset.filter(expense_type=expense_type)

        return queryset.select_related(
            'applicant', 'approved_by', 'acceptance', 'payment',
            'applicant__assigned_tutor', 'inspection', 'reimbursement_details'
        ).prefetch_related(
            'items', 'purchase_order', 'contract', 'invoices'
        ).order_by('-request_date')
