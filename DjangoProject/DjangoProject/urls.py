from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)
from users.auth_views import SafeTokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),

    # 采购模块
    path('api/procurement/', include('procurement.urls')),
    path('api/projects/', include('projects.urls')),

    # 票据/合同等模块
    path('api/invoice/', include('invoice.urls')),
    path('api/acceptance/', include('acceptance.urls')),
    path('api/payment/', include('payment.urls')),
    path('api/team-procurement/', include('team_procurement.urls')),
    path('api/group-affairs/', include('group_affairs.urls')),
    path('api/inspection/', include('inspection.urls')),
    path('api/expense-reports/', include('expense_report.urls')),
    path('api/purchase-orders/', include('purchase_order.urls')),
    path('api/contracts/', include('contract.urls')),
    path('api/reimbursement/', include('reimbursement.urls')),

    # === 新增：仪器/预约模块 ===
    path('api/equipment/', include('equipment.urls')),

    # === 新增：远程访问模块 ===
    path('api/remote_access/', include('remote_access.urls')),

    # 公告和反馈
    path('api/feedback/', include('feedback.urls')),

    # 后端只读实验室运营智能助手
    path('api/labops-agent/', include('labops_agent.urls')),

    # === 新增：走廊显示屏模块 ===
    path('api/corridor_display/', include('corridor_display.urls')),

    # JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', SafeTokenRefreshView.as_view(), name='token_refresh'),
]

# 配置媒体文件服务 (核心配置：解决图片无法访问的问题)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
