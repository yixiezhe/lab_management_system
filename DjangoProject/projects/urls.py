from django.urls import path, include
from rest_framework.routers import DefaultRouter
# --- 【新】导入 PublishedProjectListView ---
from .views import ProjectViewSet, PublishedProjectListView
# --- END ---

# 创建一个路由器并注册我们的视图集
router = DefaultRouter()
router.register(r'projects', ProjectViewSet, basename='project') # 这会处理 /projects/projects/ 相关路由

# API URL由路由器自动确定
urlpatterns = [
    # 包含由 router 自动生成的 URL (例如 /projects/projects/, /projects/projects/{pk}/ 等)
    path('', include(router.urls)),

    # --- 【新】为获取已发布项目列表添加手动路由 ---
    # 这会匹配 /projects/published-list/
    path('published-list/', PublishedProjectListView.as_view(), name='published-project-list'),
    # --- END ---
]