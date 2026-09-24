# payment/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
# --- 【修改点 1】导入我们新增的 RejectPurchaseRequestAPIView ---
from .views import PaymentViewSet, RejectPurchaseRequestAPIView

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')

urlpatterns = [
    # 保留路由器为 PaymentViewSet 自动生成的 URL
    path('', include(router.urls)),

    # --- 【修改点 2】为“付款驳回”功能添加一个专门的 URL 路径 ---
    # 前端将向 'api/payment/purchase-requests/<采购申请ID>/reject/' 发送请求
    path(
        'purchase-requests/<int:pk>/reject/',
        RejectPurchaseRequestAPIView.as_view(),
        name='reject-purchase-request'
    ),
]