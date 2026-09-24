from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
# --- 【新】导入 APIView ---
from rest_framework.views import APIView
from .models import Project
from .serializers import ProjectSerializer

# --- 【修改】移除 GlobalAnnouncement, 导入 cache 和 json ---
# from procurement.models import GlobalAnnouncement # <-- 已移除
from django.core.cache import cache
import json
# --- END OF MODIFICATION ---


# 1. 自定义权限类：只允许“项目管理员”访问 (保持不变)
class IsProjectAdmin(permissions.BasePermission):
    """
    Custom permission to only allow users with the '项目管理员' role.
    """
    message = '您没有权限管理项目。'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.roles.filter(name='项目管理员').exists()


# 2. 创建 Project 的 ModelViewSet
class ProjectViewSet(viewsets.ModelViewSet):
    """
    一个用于项目管理 (增删改查) 的视图集。
    - CRUD 操作受 IsProjectAdmin 保护。
    - 提供 'publish_list_to_homepage' action 用于将项目列表写入缓存。
    - 提供 'withdraw_homepage_publication' action 用于从缓存中删除项目列表。
    """
    queryset = Project.objects.all().order_by('-updated_at')
    serializer_class = ProjectSerializer
    permission_classes = [IsProjectAdmin]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        serializer.save(author=self.request.user)

    # --- 【修改】用于“发布列表到首页”的 action ---
    @action(
        detail=False,
        methods=['post'],
        url_path='publish-list-to-homepage',
        permission_classes=[IsProjectAdmin]
    )
    def publish_list_to_homepage(self, request):
        """
        获取所有项目，序列化为JSON，并保存到 Django 缓存中。
        """
        try:
            all_projects = self.get_queryset()
            serializer = self.get_serializer(all_projects, many=True)
            json_content = json.dumps(serializer.data, ensure_ascii=False)

            # --- 【修改】写入缓存，而不是 GlobalAnnouncement ---
            cache_key = 'published_project_list_json'
            cache.set(cache_key, json_content, timeout=None) # timeout=None 表示永不过期

            return Response(
                {"message": "项目列表已成功发布到首页缓存。"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": f"发布到缓存失败：{str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    # --- 【修改】用于“撤回发布”的 action ---
    @action(
        detail=False,
        methods=['post'],
        url_path='withdraw-homepage-publication',
        permission_classes=[IsProjectAdmin]
    )
    def withdraw_homepage_publication(self, request):
        """
        从 Django 缓存中删除已发布的项目列表。
        """
        try:
            # --- 【修改】从缓存删除，而不是 GlobalAnnouncement ---
            cache_key = 'published_project_list_json'
            deleted = cache.delete(cache_key) # delete 如果键存在则删除并返回 True，否则返回 False

            if deleted:
                return Response(
                    {"message": "已成功从首页缓存撤回项目列表。"},
                    status=status.HTTP_200_OK
                )
            else:
                 return Response(
                    {"message": "缓存中没有找到已发布的项目列表可供撤回。"},
                    status=status.HTTP_404_NOT_FOUND # 或者 200 OK
                )
        except Exception as e:
            return Response(
                {"error": f"从缓存撤回失败：{str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# --- 【新】用于首页获取已发布项目列表的视图 ---
class PublishedProjectListView(APIView):
    """
    一个公开的视图，用于获取存储在缓存中的已发布项目列表。
    """
    permission_classes = [permissions.IsAuthenticated] # 允许所有登录用户访问

    def get(self, request, *args, **kwargs):
        """
        处理 GET 请求，从缓存读取并返回项目列表。
        """
        cache_key = 'published_project_list_json'
        json_content = cache.get(cache_key)

        if not json_content:
            # 缓存中没有找到
            return Response([], status=status.HTTP_200_OK)

        try:
            # 尝试解析 JSON
            project_list_data = json.loads(json_content)

            # 确保是列表
            if not isinstance(project_list_data, list):
                 return Response([], status=status.HTTP_200_OK) # 不是列表，返回空

            # 成功，返回列表
            return Response(project_list_data, status=status.HTTP_200_OK)

        except json.JSONDecodeError:
            # 缓存内容不是有效 JSON
            return Response([], status=status.HTTP_200_OK) # 返回空
        except Exception as e:
            # 其他错误
            return Response(
                {"error": f"获取已发布项目列表失败: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )