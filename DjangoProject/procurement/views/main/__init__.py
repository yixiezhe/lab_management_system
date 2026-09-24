# procurement/views/main/__init__.py

# 【已修改】不再导入 PurchaseRequestViewSet，而是导入两个新的、分离的视图集
from .purchase_request_views import PublicPurchaseRequestViewSet, C2CPurchaseRequestViewSet, \
    StandardResultsSetPagination
from .ledger_views import FullProcessPurchaseRequestViewSet
from .utility_views import (
    DashboardStatsAPIView,
    PackageReceiptsView,
    MergeRequestsView
)

__all__ = [
    # 【已修改】导出两个新的视图集名称
    'PublicPurchaseRequestViewSet',
    'C2CPurchaseRequestViewSet',

    'FullProcessPurchaseRequestViewSet',
    'DashboardStatsAPIView',
    'PackageReceiptsView',
    'MergeRequestsView',
    'StandardResultsSetPagination',
]