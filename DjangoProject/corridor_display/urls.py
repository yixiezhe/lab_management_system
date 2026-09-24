from django.urls import path
from .views import (
    PublicDisplayAPIView,
    AdminImageListCreateAPIView,
    AdminImageDeleteAPIView,
    AdminImageReorderAPIView,
    AdminConfigAPIView,
)

urlpatterns = [
    # 公共预览（免登录）
    path('public/', PublicDisplayAPIView.as_view(), name='corridor-display-public'),

    # 管理端（需要权限）
    path('admin/images/', AdminImageListCreateAPIView.as_view(), name='corridor-display-admin-images'),
    path('admin/images/<int:pk>/', AdminImageDeleteAPIView.as_view(), name='corridor-display-admin-image-delete'),
    path('admin/images/reorder/', AdminImageReorderAPIView.as_view(), name='corridor-display-admin-images-reorder'),
    path('admin/config/', AdminConfigAPIView.as_view(), name='corridor-display-admin-config'),
]
