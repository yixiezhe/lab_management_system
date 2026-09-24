# procurement/views/admin.py

# --- 【修改】移除 json, 保留 Response 和 status (以防万一) ---
from rest_framework import viewsets, filters, generics, permissions, status
from rest_framework.response import Response
# import json # <-- 已移除
# --- END OF MODIFICATION ---

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import F, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from ..models import AnnouncementRead, WhitelistItem, Platform, GlobalAnnouncement, PublicProcurementDutySchedule
# --- 【修改】导入正确的权限类 ---
from ..permissions import CanManageWhitelist, IsChiefSteward, IsProjectAdmin, IsSystemAdmin, \
    CanModifyWhitelist, IsAnnouncementAdmin, IsNotLandHost  # <-- 导入 CanModifyWhitelist
from ..serializers import WhitelistItemSerializer, PlatformSerializer, GlobalAnnouncementSerializer, PublicProcurementDutyScheduleSerializer


class WhitelistItemViewSet(viewsets.ModelViewSet):
    queryset = WhitelistItem.objects.all().order_by('main_category', 'platform', 'content')
    serializer_class = WhitelistItemSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['content', 'platform', 'manufacturer', 'cas_number', 'product_number']

    # --- (WhitelistItemViewSet 的 get_permissions 保持不变) ---
    def get_permissions(self):
        """
        根据操作类型设置不同的权限。
        查看：允许所有登录用户。
        修改：只允许特定角色 (系统管理员, 大总管, 导师用户)。
        """
        # --- 【调试打印 开始】 ---
        print(f"--- WhitelistItemViewSet get_permissions ---")
        print(f"Action: {self.action}")  # 打印当前请求的操作类型

        permission_classes = []  # 初始化为空列表
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.IsAuthenticated]  # 使用导入的 permissions.IsAuthenticated
            print("Selected permission: IsAuthenticated")  # 打印选择的权限
        else:  # create, update, partial_update, destroy
            permission_classes = [CanModifyWhitelist]
            print("Selected permission: CanModifyWhitelist")  # 打印选择的权限

        # 实例化并检查每个权限类的结果
        final_permissions = []
        for permission_class in permission_classes:
            permission_instance = permission_class()
            # 尝试手动调用 has_permission 检查 (如果适用)
            try:
                # 对于 list 操作，Django REST Framework 主要检查 has_permission
                has_perm = permission_instance.has_permission(self.request, self)
                print(f"Checking {permission_class.__name__}.has_permission: {has_perm}")
                if not has_perm:
                    print(f"DEBUG: Permission denied by {permission_class.__name__}")
            except Exception as e:
                print(f"Error checking permission {permission_class.__name__}: {e}")

            final_permissions.append(permission_instance)  # 无论检查结果如何，都按DRF流程返回实例

        print(f"--- End WhitelistItemViewSet get_permissions ---")
        # --- 【调试打印 结束】 ---
        return final_permissions  # 返回实例化后的列表

    # --- 【修正结束】 ---

    def get_queryset(self):
        queryset = super().get_queryset()
        platform = self.request.query_params.get('platform')
        main_category = self.request.query_params.get('main_category')
        purchase_type = self.request.query_params.get('purchase_type')
        if platform: queryset = queryset.filter(Q(platform=platform) | Q(platform__isnull=True) | Q(platform=""))
        if main_category: queryset = queryset.filter(main_category__contains=main_category)
        if purchase_type: queryset = queryset.filter(purchase_type=purchase_type)
        return queryset


class PlatformViewSet(viewsets.ModelViewSet):
    # --- (PlatformViewSet 保持不变) ---
    queryset = Platform.objects.prefetch_related('managers').all()
    serializer_class = PlatformSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsChiefSteward]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()


class GlobalAnnouncementViewSet(viewsets.ModelViewSet):
    """
    多公告接口。
    - list/retrieve: 登录用户可读。
    - create/update: 项目管理员、系统管理员或超级用户可管理。
    - home: 首页展示公告。
    - unread-popup: 当前用户未读且需要弹窗的公告。
    - mark-read: 将指定公告标记为已读。
    """
    serializer_class = GlobalAnnouncementSerializer
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = (
            GlobalAnnouncement.objects
            .select_related('created_by', 'updated_by')
            .exclude(content='')
            .order_by('-created_at', '-id')
        )
        if self.action == 'home':
            queryset = queryset.filter(is_published=True)
        if self.action == 'unread_popup':
            user = self.request.user
            queryset = queryset.filter(show_popup=True).exclude(
                read_records__user=user,
                read_records__read_at__gte=F('updated_at'),
            )
        return queryset

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            self.permission_classes = [IsAnnouncementAdmin]
        elif self.action in ['unread_popup', 'mark_read', 'mark_all_read']:
            self.permission_classes = [IsAuthenticated, IsNotLandHost]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='home')
    def home(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='unread-popup')
    def unread_popup(self, request):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        announcement = self.get_object()
        read_record, _ = AnnouncementRead.objects.update_or_create(
            announcement=announcement,
            user=request.user,
            defaults={'read_at': timezone.now()},
        )
        return Response(
            {
                'id': announcement.id,
                'read_at': read_record.read_at,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        announcements = self.get_queryset()
        now = timezone.now()
        for announcement in announcements:
            AnnouncementRead.objects.update_or_create(
                announcement=announcement,
                user=request.user,
                defaults={'read_at': now},
            )
        return Response({'marked_count': announcements.count()}, status=status.HTTP_200_OK)


class GlobalAnnouncementView(generics.RetrieveUpdateAPIView):
    """
    兼容旧版单公告接口。新前端使用 /announcements/。
    """
    serializer_class = GlobalAnnouncementSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            self.permission_classes = [IsAnnouncementAdmin]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_object(self):
        return GlobalAnnouncement.load()

    def perform_update(self, serializer):
        # 更新 (PUT/PATCH) 逻辑保持不变
        serializer.save(updated_by=self.request.user)

    # --- 【已移除】之前重写的 retrieve 方法 ---
    # def retrieve(self, request, *args, **kwargs):
    #     ...

class PublicProcurementDutyScheduleView(generics.RetrieveUpdateAPIView):
    """
    公共经费采购流程“每周采购人”配置接口。
    GET: 所有登录用户可读（保证页面上所有人看到同一份设置）
    PUT/PATCH: 仅系统管理员可写
    """
    serializer_class = PublicProcurementDutyScheduleSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            self.permission_classes = [IsSystemAdmin]
        else:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def get_object(self):
        return PublicProcurementDutySchedule.load()

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
