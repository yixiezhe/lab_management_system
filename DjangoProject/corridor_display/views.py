from urllib.parse import urljoin

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from rest_framework.parsers import MultiPartParser, FormParser

from .models import DisplayImage, DisplayConfig
from .serializers import (
    DisplayImageSerializer,
    DisplayImageUploadSerializer,
    DisplayConfigSerializer,
)

def _notes_to_list(notes):
    """保证 notes 一定是 list，前端 v-for 才不会出问题。"""
    if notes is None:
        return []
    if isinstance(notes, list):
        return notes
    if isinstance(notes, str):
        return [x.strip() for x in notes.splitlines() if x.strip()]
    return []


# =========================
# 权限：系统管理员 / 走廊显示屏管理人员
# =========================
class IsCorridorScreenManagerOrSystemAdmin(BasePermission):
    """
    仅允许：
    - Django superuser
    - 角色包含 “系统管理员”
    - 角色包含 “走廊显示屏管理人员”
    """

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        if getattr(user, "is_superuser", False):
            return True

        try:
            return user.roles.filter(name__in=["系统管理员", "走廊显示屏管理人员"]).exists()
        except Exception:
            return False


# =========================
# 公共接口：预览页用（免登录）
# GET /api/corridor_display/public/
# =========================
class PublicDisplayAPIView(APIView):
    permission_classes = []
    authentication_classes = []  # 明确禁用默认鉴权（避免一些环境下带 token/代理导致奇怪行为）

    def get(self, request, *args, **kwargs):
        cfg = DisplayConfig.get_solo()
        imgs = DisplayImage.objects.all().order_by("order", "created_at")

        # 统一构建前端需要的 payload
        images_payload = []
        for img in imgs:
            # ✅ 强制只返回相对路径，把拼接域名的工作交给前端 resolveUrl
            # 这样无论是 localhost 还是 192.168.x.x 访问，都不会有跨域/混合内容问题
            rel_url = ""
            try:
                if img.image:
                    rel_url = img.image.url
            except Exception:
                pass

            images_payload.append({
                "id": img.id,
                "name": getattr(img, "name", "") or "",
                "url": rel_url, # 例如 /media/images/1.jpg
                "order": getattr(img, "order", None),
            })

        return Response(
            {
                "carousel_interval_ms": cfg.carousel_interval_ms,
                "images": images_payload,
                "duty": {
                    "text": cfg.duty_text,
                    "week1_start": cfg.duty_week1_start.isoformat() if getattr(cfg, "duty_week1_start", None) else None,
                    "rotation_unit": cfg.duty_rotation_unit,
                    "package_duty_list": _notes_to_list(cfg.package_duty_list),
                    "lab_duty_groups": _notes_to_list(cfg.lab_duty_groups),
                },
                "status": {
                    "state": cfg.state,
                    "tip": cfg.tip,
                    "safety": cfg.safety,
                    "notes": _notes_to_list(cfg.notes),
                    "updated_at": cfg.updated_at.isoformat() if getattr(cfg, "updated_at", None) else None,
                },
            },
            status=status.HTTP_200_OK,
        )


# =========================
# 管理端：图片列表 / 上传
# GET  /api/corridor_display/admin/images/
# POST /api/corridor_display/admin/images/   (multipart: image, name?)
# =========================
class AdminImageListCreateAPIView(APIView):
    permission_classes = [IsCorridorScreenManagerOrSystemAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, *args, **kwargs):
        imgs = DisplayImage.objects.all().order_by("order", "created_at")
        # 这里的 Serializer 已经被修改为只返回相对路径了
        data = DisplayImageSerializer(imgs, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        ser = DisplayImageUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        obj = ser.save()
        out = DisplayImageSerializer(obj, context={"request": request}).data
        return Response(out, status=status.HTTP_201_CREATED)


# =========================
# 管理端：删除图片
# DELETE /api/corridor_display/admin/images/<id>/
# =========================
class AdminImageDeleteAPIView(APIView):
    permission_classes = [IsCorridorScreenManagerOrSystemAdmin]

    def delete(self, request, pk, *args, **kwargs):
        img = get_object_or_404(DisplayImage, pk=pk)
        img.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# =========================
# 管理端：排序
# POST /api/corridor_display/admin/images/reorder/
# body: { "ordered_ids": [3,1,2,...] }
# =========================
class AdminImageReorderAPIView(APIView):
    permission_classes = [IsCorridorScreenManagerOrSystemAdmin]

    def post(self, request, *args, **kwargs):
        ordered_ids = request.data.get("ordered_ids", [])
        if not isinstance(ordered_ids, list) or not all(isinstance(x, int) for x in ordered_ids):
            return Response(
                {"error": "ordered_ids 必须是整数数组。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        seen = set()
        ordered_ids_unique = []
        for x in ordered_ids:
            if x not in seen:
                seen.add(x)
                ordered_ids_unique.append(x)

        imgs = list(DisplayImage.objects.all().order_by("order", "created_at"))
        img_map = {img.id: img for img in imgs}

        new_order_list = [img_id for img_id in ordered_ids_unique if img_id in img_map]
        remaining = [img.id for img in imgs if img.id not in set(new_order_list)]
        final_ids = new_order_list + remaining

        with transaction.atomic():
            for idx, img_id in enumerate(final_ids, start=1):
                DisplayImage.objects.filter(id=img_id).update(order=idx)

        imgs2 = DisplayImage.objects.all().order_by("order", "created_at")
        data = DisplayImageSerializer(imgs2, many=True, context={"request": request}).data
        return Response(data, status=status.HTTP_200_OK)


# =========================
# 管理端：配置读取/保存（单例）
# GET /api/corridor_display/admin/config/
# PUT /api/corridor_display/admin/config/
# =========================
class AdminConfigAPIView(APIView):
    permission_classes = [IsCorridorScreenManagerOrSystemAdmin]

    def get(self, request, *args, **kwargs):
        cfg = DisplayConfig.get_solo()
        data = DisplayConfigSerializer(cfg).data
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request, *args, **kwargs):
        cfg = DisplayConfig.get_solo()
        ser = DisplayConfigSerializer(cfg, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data, status=status.HTTP_200_OK)
