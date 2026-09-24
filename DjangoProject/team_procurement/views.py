from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
# --- 【修改点 1】修正导入路径 ---
from django_filters.rest_framework import DjangoFilterBackend
from procurement.views.main import StandardResultsSetPagination  # 复用公共模块定义好的分页类
from .filters import TeamLedgerFilter

from .models import TeamPurchaseRequest
from .serializers import TeamPurchaseRequestSerializer, FullProcessTeamPurchaseRequestSerializer
from .permissions import TeamLedgerAccessPermission
from procurement.permissions import CanApproveTeamRequest, IsOwnerAndPending


class TeamPurchaseRequestViewSet(viewsets.ModelViewSet):
    """
    小组请购申请的API视图。
    - 普通用户可以创建、查看自己的申请。
    - 小组导师和小组采购员可以查看和审批自己小组内的所有申请。
    """
    queryset = TeamPurchaseRequest.objects.all().order_by('-request_date')
    serializer_class = TeamPurchaseRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        user_roles = set(user.roles.values_list('name', flat=True))

        status_filter = self.request.query_params.get('status')
        status_in_filter = self.request.query_params.get('status__in')

        base_queryset = self.queryset
        if status_filter:
            base_queryset = base_queryset.filter(status=status_filter)
        if status_in_filter:
            statuses = [s.strip() for s in status_in_filter.split(',')]
            base_queryset = base_queryset.filter(status__in=statuses)

        is_team_approver = '导师用户' in user_roles or '小组采购人员' in user_roles

        if is_team_approver:
            if '导师用户' in user_roles:
                return base_queryset.filter(tutor=user)
            elif '小组采购人员' in user_roles and user.assigned_tutor:
                return base_queryset.filter(tutor=user.assigned_tutor)
            else:
                return self.queryset.none()
        else:
            return base_queryset.filter(applicant=user)

    def perform_create(self, serializer):
        serializer.save(applicant=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTeamRequest])
    def approve(self, request, pk=None):
        purchase_request = self.get_object()
        purchase_request.status = 'approved'
        purchase_request.approved_by = request.user
        purchase_request.rejection_reason = None
        purchase_request.save()
        return Response({'status': '申请已批准'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[CanApproveTeamRequest])
    def reject(self, request, pk=None):
        purchase_request = self.get_object()
        reason = request.data.get('reason', '未提供原因')
        purchase_request.status = 'rejected'
        purchase_request.rejection_reason = reason
        purchase_request.save()
        return Response({'status': '申请已驳回'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerAndPending])
    def withdraw(self, request, pk=None):
        purchase_request = self.get_object()
        purchase_request.status = 'withdrawn'
        purchase_request.save()
        return Response({'status': '申请已撤回'}, status=status.HTTP_200_OK)


class FullProcessTeamPurchaseRequestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    小组采购台账的只读API视图。
    - 导师可以看到自己小组的完整台账。
    - 小组采购人员可以看到自己所在小组的完整台账。
    - 系统管理员可以看到所有小组的台账。
    """
    serializer_class = FullProcessTeamPurchaseRequestSerializer
    permission_classes = [IsAuthenticated, TeamLedgerAccessPermission]

    # --- 【修改点 2】启用分页、筛选和搜索功能 ---
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TeamLedgerFilter
    search_fields = [
        'applicant__name',
        'tutor__name',
        'items__content',
        'items__specifications',
    ]

    def get_queryset(self):
        user = self.request.user
        user_roles = set(user.roles.values_list('name', flat=True))

        queryset = TeamPurchaseRequest.objects.filter(
            status__in=['approved', 'paid', 'ordered', 'invoiced', 'accepted']
        )

        if '系统管理员' in user_roles:
            pass
        elif '导师用户' in user_roles:
            queryset = queryset.filter(tutor=user)
        elif '小组采购人员' in user_roles:
            if user.assigned_tutor:
                queryset = queryset.filter(tutor=user.assigned_tutor)
            else:
                return TeamPurchaseRequest.objects.none()
        else:
            return TeamPurchaseRequest.objects.none()

        return queryset.select_related(
            'applicant', 'tutor', 'approved_by'
        ).prefetch_related(
            'items'
        ).order_by('-request_date')