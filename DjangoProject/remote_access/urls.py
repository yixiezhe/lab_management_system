from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RdpMachineViewSet, RdpBookingViewSet, DeviceLoginView

# 1. 创建一个 DRF 路由器
router = DefaultRouter()

# 2. 注册 ViewSet
# 注册 'machines' 路由，用于获取主机列表
# /api/remote_access/machines/
router.register(r'machines', RdpMachineViewSet, basename='rdp-machine')

# 注册 'bookings' 路由，用于创建、获取和管理预约
# /api/remote_access/bookings/
# /api/remote_access/bookings/my/
# /api/remote_access/bookings/{id}/cancel/
# /api/remote_access/bookings/{id}/connect/
router.register(r'bookings', RdpBookingViewSet, basename='rdp-booking')

# 3. 定义 urlpatterns
# Django 会自动包含 router.urls
urlpatterns = [
    path('device_login/', DeviceLoginView.as_view(), name='device-login'),
    path('', include(router.urls)),
]
