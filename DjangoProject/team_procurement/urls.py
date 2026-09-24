from django.urls import path, include
from rest_framework.routers import DefaultRouter
# --- 【修改点 1】导入新增的台账视图 ---
from .views import TeamPurchaseRequestViewSet, FullProcessTeamPurchaseRequestViewSet

router = DefaultRouter()
router.register(r'requests', TeamPurchaseRequestViewSet, basename='team_purchase_request')
# --- 【修改点 2】为新的台账视图注册 URL ---
router.register(r'full-process-requests', FullProcessTeamPurchaseRequestViewSet, basename='team_ledger')

urlpatterns = [
    path('', include(router.urls)),
]