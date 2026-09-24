from rest_framework.routers import DefaultRouter
# --- 【新】导入 ReimbursementViewSet ---
from .views import PublicExpenseRecordViewSet, C2CExpenseRecordViewSet, ReimbursementViewSet
# --- END ---

router = DefaultRouter()
router.register(r'public-expenses', PublicExpenseRecordViewSet, basename='public-expense')
router.register(r'c2c-expenses', C2CExpenseRecordViewSet, basename='c2c-expense')

# --- 【新】注册 ReimbursementViewSet ---
# 这将创建 /reimbursement/reimbursements/ 等 URL
router.register(r'reimbursements', ReimbursementViewSet, basename='reimbursement')
# --- END ---

urlpatterns = router.urls