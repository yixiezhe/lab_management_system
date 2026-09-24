from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AcceptanceViewSet

# 创建一个 DRF 的路由器实例
router = DefaultRouter()

# 将 AcceptanceViewSet 注册到路由器中
# 这会自动生成验收信息的增删改查URL
router.register(r'acceptances', AcceptanceViewSet, basename='acceptance')

# 定义 app 的 URL 模式
urlpatterns = [
    # 将路由器生成的所有 URL 包含进来
    path('', include(router.urls)),
]