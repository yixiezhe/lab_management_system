from django.urls import path, include
from rest_framework.routers import DefaultRouter
# --- START: 核心修改 ---
# 我们只导入 InvoiceViewSet，因为 ApprovedRequestWithInvoiceViewSet 已经被移除了
from .views import InvoiceViewSet
# --- END: 核心修改 ---

# 1. 创建一个 DRF 的路由器实例
router = DefaultRouter()

# 2. 将我们的 ViewSet 注册到路由器中
# 为 InvoiceViewSet 自动生成 URL (例如: GET /invoices/, POST /invoices/, GET /invoices/1/, PUT /invoices/1/)
router.register(r'invoices', InvoiceViewSet, basename='invoice')

# --- START: 核心修改 ---
# 移除了下面这行，因为它引用的视图已经不存在了
# router.register(r'full-info-requests', ApprovedRequestWithInvoiceViewSet, basename='full-info-request')
# --- END: 核心修改 ---

# 3. 定义 app 的 URL 模式
urlpatterns = [
    # 将路由器生成的所有 URL 包含进来
    path('', include(router.urls)),
]