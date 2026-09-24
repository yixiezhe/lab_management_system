from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.main import purchase_request_views as main
from .views import admin
from .views.main.ledger_views import FullProcessPurchaseRequestViewSet
from .views.main.report_views import PublicExpenseReportView
from .views.main.utility_views import DashboardStatsAPIView, PackageReceiptsView, MergeRequestsView, \
    PackageAttachmentsView, PackageReimbursementImagesView, BulkDeleteRequestsView, UnmergeRequestView, \
    ExportC2CPlatformRecordsView

router = DefaultRouter()

router.register(r'public-purchase-requests', main.PublicPurchaseRequestViewSet, basename='public-purchase-request')
router.register(r'c2c-purchase-requests', main.C2CPurchaseRequestViewSet, basename='c2c-purchase-request')
router.register(r'whitelist-items', admin.WhitelistItemViewSet, basename='whitelist-item')
router.register(r'full-process-requests', FullProcessPurchaseRequestViewSet, basename='full-process-request')
router.register(r'platforms', admin.PlatformViewSet, basename='platform')
router.register(r'announcements', admin.GlobalAnnouncementViewSet, basename='announcement')

urlpatterns = [
    path('', include(router.urls)),

    path('dashboard-stats/', DashboardStatsAPIView.as_view(), name='dashboard-stats'),
    path('public-expense-report/', PublicExpenseReportView.as_view(), name='public-expense-report'),
    path('package-receipts/', PackageReceiptsView.as_view(), name='package-receipts'),
    path('merge-requests/', MergeRequestsView.as_view(), name='merge-requests'),
    path('requests/<int:pk>/unmerge/', UnmergeRequestView.as_view(), name='unmerge-request'),
    path('announcement/', admin.GlobalAnnouncementView.as_view(), name='global-announcement'),
    path('public-duty-schedule/', admin.PublicProcurementDutyScheduleView.as_view(), name='public-duty-schedule'),
    path('requests/<int:pk>/package-attachments/', PackageAttachmentsView.as_view(), name='package-attachments'),
    path('requests/<int:pk>/package-reimbursement-images/', PackageReimbursementImagesView.as_view(),
         name='package-reimbursement-images'),
    path('c2c-platform-records-export/', ExportC2CPlatformRecordsView.as_view(), name='c2c-platform-records-export'),

    # --- 【新功能】 ---
    # 添加批量删除的URL路由
    path('bulk-delete-requests/', BulkDeleteRequestsView.as_view(), name='bulk-delete-requests'),
    # --- 【新功能结束】 ---
]
