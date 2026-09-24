from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q
from .models import RdpMachine, RdpBooking, MAX_REMOTE_BOOKING_DURATION, get_remote_booking_effective_end_time
from .serializers import (
    RdpMachineSerializer,
    RdpBookingSerializer,
    RdpBookingCreateSerializer,
    DeviceLoginSerializer
)
from .permissions import IsSystemAdminOrReadOnly, check_is_system_admin
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

import base64
from django.conf import settings
import requests
import datetime
import os
from django.utils.timezone import make_aware, get_current_timezone

# ==========================================
# 配置区域
# ==========================================
GUACAMOLE_URL = os.getenv("GUACAMOLE_URL", "http://localhost:8080/guacamole")
GUACAMOLE_INTERNAL_API_URL = os.getenv("GUACAMOLE_INTERNAL_API_URL", "http://localhost:8080/guacamole/api")
GUAC_ADMIN_USER = os.getenv("GUAC_ADMIN_USER", "guacadmin")
GUAC_ADMIN_PASSWORD = os.getenv("GUAC_ADMIN_PASSWORD", "")
GUAC_AUTH_PROVIDER = "postgresql"
TAKEOVER_TIMEOUT_SECONDS = 60
TAKEOVER_REJECTED_COOLDOWN_SECONDS = 5 * 60
GUACAMOLE_REQUEST_TIMEOUT = 3
GUACAMOLE_TOKEN_REUSE_SECONDS = 50 * 60
GUACAMOLE_AUTH_CACHE = {
    "session": None,
    "api_url": "",
    "auth_token": "",
    "issued_at": None,
}


def get_guacamole_api_urls():
    urls = []
    for url in [
        GUACAMOLE_INTERNAL_API_URL,
        f"{GUACAMOLE_URL.rstrip('/')}/api",
    ]:
        if url and url not in urls:
            urls.append(url)
    return urls


def guacamole_debug(message):
    try:
        log_dir = settings.BASE_DIR.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "remote_guacamole_disconnect.log"
        ts = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


def new_guacamole_session():
    session = requests.Session()
    # 实验室主机上可能存在系统代理，内网 Guacamole 请求必须直连。
    session.trust_env = False
    return session


def get_guacamole_auth_context(force_refresh=False):
    cached_token = GUACAMOLE_AUTH_CACHE.get("auth_token")
    cached_issued_at = GUACAMOLE_AUTH_CACHE.get("issued_at")
    if not force_refresh and cached_token and cached_issued_at:
        age = (timezone.now() - cached_issued_at).total_seconds()
        if age < GUACAMOLE_TOKEN_REUSE_SECONDS:
            return (
                GUACAMOLE_AUTH_CACHE.get("session") or new_guacamole_session(),
                GUACAMOLE_AUTH_CACHE.get("api_url") or "",
                cached_token
            )

    for api_url in get_guacamole_api_urls():
        session = new_guacamole_session()
        try:
            resp = session.post(
                f"{api_url}/tokens",
                data={"username": GUAC_ADMIN_USER, "password": GUAC_ADMIN_PASSWORD},
                timeout=GUACAMOLE_REQUEST_TIMEOUT
            )
            if resp.status_code == 200:
                auth_token = resp.json().get("authToken")
                if auth_token:
                    GUACAMOLE_AUTH_CACHE.update({
                        "session": session,
                        "api_url": api_url,
                        "auth_token": auth_token,
                        "issued_at": timezone.now(),
                    })
                    return session, api_url, auth_token
            guacamole_debug(f"AUTH_FAIL: api={api_url} | status={resp.status_code} | body={resp.text[:200]}")
        except Exception as e:
            guacamole_debug(f"AUTH_ERROR: api={api_url} | error={repr(e)}")
    return None, "", ""


def clear_guacamole_auth_cache():
    GUACAMOLE_AUTH_CACHE.update({
        "session": None,
        "api_url": "",
        "auth_token": "",
        "issued_at": None,
    })


def find_guacamole_connection_identifier(machine, session, api_url, auth_token, allow_model_fallback=True):
    headers = {"Guacamole-Token": auth_token}
    try:
        tree_resp = session.get(
            f"{api_url}/session/data/{GUAC_AUTH_PROVIDER}/connectionGroups/ROOT/tree",
            headers=headers,
            timeout=GUACAMOLE_REQUEST_TIMEOUT
        )
        if tree_resp.status_code in (401, 403):
            clear_guacamole_auth_cache()
            guacamole_debug(
                f"TREE_AUTH_EXPIRED: machine={machine.name} | status={tree_resp.status_code}"
            )
        elif tree_resp.status_code != 200:
            guacamole_debug(
                f"TREE_FAIL: machine={machine.name} | status={tree_resp.status_code} | body={tree_resp.text[:200]}"
            )
        else:
            def walk(group):
                for conn in group.get("childConnections", []) or []:
                    if conn.get("name") == machine.name:
                        return str(conn.get("identifier") or "")
                for child in group.get("childConnectionGroups", []) or []:
                    found = walk(child)
                    if found:
                        return found
                return ""

            identifier = walk(tree_resp.json())
            if identifier:
                return identifier
    except Exception as e:
        guacamole_debug(f"TREE_ERROR: machine={machine.name} | error={repr(e)}")

    if allow_model_fallback and machine.guacamole_id:
        return str(machine.guacamole_id)
    return ""


def disconnect_guacamole_active_connections_for_booking(booking, reason):
    """
    只断开 Guacamole 当前活跃连接，不注销 Windows 会话。
    失败不影响数据库释放，避免 Guacamole 短暂不可用时卡住登出/插队。
    """
    try:
        machine = booking.machine
    except Exception:
        return 0

    session, api_url, auth_token = get_guacamole_auth_context()
    if not auth_token:
        guacamole_debug(f"SKIP_NO_AUTH: booking={booking.id} | reason={reason}")
        return 0

    connection_identifier = find_guacamole_connection_identifier(machine, session, api_url, auth_token)
    if not connection_identifier:
        session, api_url, auth_token = get_guacamole_auth_context(force_refresh=True)
        if auth_token:
            connection_identifier = find_guacamole_connection_identifier(machine, session, api_url, auth_token)
    if not connection_identifier:
        guacamole_debug(f"SKIP_NO_CONNECTION_ID: booking={booking.id} | machine={machine.name} | reason={reason}")
        return 0

    headers = {"Guacamole-Token": auth_token}
    try:
        active_resp = session.get(
            f"{api_url}/session/data/{GUAC_AUTH_PROVIDER}/activeConnections",
            headers=headers,
            timeout=GUACAMOLE_REQUEST_TIMEOUT
        )
        if active_resp.status_code in (401, 403):
            clear_guacamole_auth_cache()
            session, api_url, auth_token = get_guacamole_auth_context(force_refresh=True)
            headers = {"Guacamole-Token": auth_token}
            if auth_token:
                active_resp = session.get(
                    f"{api_url}/session/data/{GUAC_AUTH_PROVIDER}/activeConnections",
                    headers=headers,
                    timeout=GUACAMOLE_REQUEST_TIMEOUT
                )

        if active_resp.status_code != 200:
            guacamole_debug(
                f"ACTIVE_FAIL: booking={booking.id} | status={active_resp.status_code} | body={active_resp.text[:200]}"
            )
            return 0

        active_data = active_resp.json()
        if isinstance(active_data, dict):
            active_connections = active_data.values()
        elif isinstance(active_data, list):
            active_connections = active_data
        else:
            active_connections = []

        disconnected = 0
        for active in active_connections:
            if str(active.get("connectionIdentifier") or "") != str(connection_identifier):
                continue

            active_identifier = active.get("identifier")
            if not active_identifier:
                continue

            delete_resp = session.delete(
                f"{api_url}/session/data/{GUAC_AUTH_PROVIDER}/activeConnections/{active_identifier}",
                headers=headers,
                timeout=GUACAMOLE_REQUEST_TIMEOUT
            )
            if delete_resp.status_code in (200, 202, 204):
                disconnected += 1
                guacamole_debug(
                    f"DISCONNECT_OK: booking={booking.id} | machine={machine.name} | active={active_identifier} | reason={reason}"
                )
            else:
                guacamole_debug(
                    f"DISCONNECT_FAIL: booking={booking.id} | active={active_identifier} | status={delete_resp.status_code} | body={delete_resp.text[:200]}"
                )

        if disconnected == 0:
            guacamole_debug(
                f"DISCONNECT_NONE: booking={booking.id} | machine={machine.name} | conn={connection_identifier} | reason={reason}"
            )
        return disconnected
    except Exception as e:
        guacamole_debug(f"DISCONNECT_ERROR: booking={booking.id} | reason={reason} | error={repr(e)}")
        return 0


def get_booking_effective_end_time(booking):
    """单次远程连接最多 30 分钟，兼容旧的更长预约记录。"""
    return get_remote_booking_effective_end_time(booking.start_time, booking.end_time)


def complete_expired_remote_booking(booking, now=None):
    now = now or timezone.now()
    if booking.status not in ['confirmed', 'active']:
        return False

    effective_end_time = get_booking_effective_end_time(booking)
    if now < effective_end_time:
        return False

    booking.status = 'completed'
    booking.real_end_time = now
    booking.termination_reason = 'forced'
    booking.save()
    disconnect_guacamole_active_connections_for_booking(booking, 'time_up')
    return True


def get_takeover_remaining_seconds(booking, now=None):
    if booking.takeover_status != 'pending' or not booking.takeover_requested_at:
        return None

    now = now or timezone.now()
    elapsed_seconds = (now - booking.takeover_requested_at).total_seconds()
    return max(0, int(TAKEOVER_TIMEOUT_SECONDS - elapsed_seconds))


def get_takeover_rejected_cooldown_remaining_seconds(booking, user, now=None):
    if booking.takeover_status != 'rejected' or not booking.takeover_requested_at:
        return 0
    if booking.takeover_applicant_id != getattr(user, 'id', None):
        return 0

    now = now or timezone.now()
    elapsed_seconds = (now - booking.takeover_requested_at).total_seconds()
    return max(0, int(TAKEOVER_REJECTED_COOLDOWN_SECONDS - elapsed_seconds))


def complete_takeover_timeout_booking(booking, now=None):
    now = now or timezone.now()
    if booking.status not in ['confirmed', 'active']:
        return False
    if booking.takeover_status != 'pending' or not booking.takeover_requested_at:
        return False

    elapsed_seconds = (now - booking.takeover_requested_at).total_seconds()
    if elapsed_seconds < TAKEOVER_TIMEOUT_SECONDS:
        return False

    booking.status = 'completed'
    booking.real_end_time = now
    booking.termination_reason = 'takeover'
    booking.takeover_status = 'approved'
    booking.save()
    disconnect_guacamole_active_connections_for_booking(booking, 'takeover_timeout')
    return True


def advance_remote_booking_state(booking, now=None):
    """
    推进远程预约状态。
    这个逻辑必须能被任何轮询入口触发，不能只依赖正在使用者的活跃页面。
    """
    now = now or timezone.now()
    if booking.status not in ['confirmed', 'active']:
        return None
    if complete_takeover_timeout_booking(booking, now):
        return 'takeover_timeout'
    if complete_expired_remote_booking(booking, now):
        return 'time_up'
    return None


def build_takeover_status_payload(booking, now=None):
    remaining_seconds = get_takeover_remaining_seconds(booking, now)
    expires_at = None
    if booking.takeover_requested_at:
        expires_at = booking.takeover_requested_at + timezone.timedelta(seconds=TAKEOVER_TIMEOUT_SECONDS)

    return {
        "takeover_status": booking.takeover_status,
        "takeover_requested_at": booking.takeover_requested_at,
        "takeover_timeout_seconds": TAKEOVER_TIMEOUT_SECONDS,
        "takeover_remaining_seconds": remaining_seconds,
        "takeover_expires_at": expires_at,
    }


def device_login_debug(message):
    try:
        log_dir = settings.BASE_DIR.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "remote_device_login_debug.log"
        ts = timezone.localtime(timezone.now()).strftime("%Y-%m-%d %H:%M:%S")
        with log_file.open("a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        pass


# [核心] 全能型姓名获取函数 (保持不变)
def get_user_display_name(user):
    if not user:
        return ""
    if hasattr(user, 'name') and user.name:
        return str(user.name).strip()
    if hasattr(user, 'real_name') and user.real_name:
        return str(user.real_name).strip()
    if hasattr(user, 'chinese_name') and user.chinese_name:
        return str(user.chinese_name).strip()
    for rel_name in ['userprofile', 'profile']:
        if hasattr(user, rel_name):
            try:
                profile = getattr(user, rel_name)
                for field in ['name', 'real_name', 'chinese_name', 'xm']:
                    if hasattr(profile, field) and getattr(profile, field):
                        val = getattr(profile, field)
                        if val: return str(val).strip()
            except:
                pass
    full_name = user.get_full_name()
    if full_name and full_name.strip():
        return full_name.strip()
    if user.first_name and user.first_name.strip():
        return user.first_name.strip()
    return user.username


# ==========================================

class DeviceLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = DeviceLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device_login_debug(
            "STEP 1 request accepted | keys=" + ",".join(sorted(request.data.keys()))
            + " | local_user=" + str(request.data.get("local_user", ""))
            + " | machine_id=" + str(request.data.get("machine_id", ""))
            + " | machine_name=" + str(request.data.get("machine_name", ""))
            + " | has_device_secret=" + str(bool(request.data.get("device_secret")))
        )
        machine_id = serializer.validated_data.get("machine_id")
        machine_name = serializer.validated_data.get("machine_name")
        local_user = serializer.validated_data.get("local_user")
        device_secret = (serializer.validated_data.get("device_secret") or "").strip()

        normalized_local_user = (local_user or "").strip()
        has_device_secret = bool(device_secret)
        machine = None
        if machine_id is not None:
            try:
                machine = RdpMachine.objects.get(pk=machine_id, is_active=True)
            except RdpMachine.DoesNotExist:
                machine = None
        if machine is None and machine_name:
            try:
                machine = RdpMachine.objects.get(name=machine_name, is_active=True)
            except RdpMachine.DoesNotExist:
                machine = None
        if machine is None and normalized_local_user:
            machine = RdpMachine.objects.filter(
                Q(username__iexact=normalized_local_user) | Q(name__iexact=normalized_local_user),
                is_active=True
            ).first()
        if machine is None:
            device_login_debug("ERROR STEP 2 machine not found | local_user=" + normalized_local_user)
            return Response({"detail": "设备不存在或未启用", "debug_step": "machine_not_found"}, status=status.HTTP_404_NOT_FOUND)
        device_login_debug("STEP 2 machine matched | id=" + str(machine.id) + " | name=" + machine.name + " | username=" + (machine.username or "") + " | has_device_secret=" + str(has_device_secret))

        if has_device_secret:
            if not machine.verify_device_secret(device_secret):
                device_login_debug("ERROR STEP 3 device_secret mismatch | machine_id=" + str(machine.id) + " | local_user=" + normalized_local_user)
                return Response({"detail": "设备密钥错误", "debug_step": "device_secret_mismatch"}, status=status.HTTP_403_FORBIDDEN)
            device_login_debug("STEP 3 device_secret verified")
        elif not normalized_local_user:
            device_login_debug("ERROR STEP 3 missing local_user without device_secret")
            return Response({"detail": "缺少本机用户名", "debug_step": "missing_local_user"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            device_login_debug("STEP 3 no device_secret provided, using same-name land-host login")

        machine_username = (machine.username or "").strip()
        machine_name_value = (machine.name or "").strip()
        if normalized_local_user and machine_username and machine_username.lower() != normalized_local_user.lower() and machine_name_value.lower() != normalized_local_user.lower():
            device_login_debug("ERROR STEP 4 local_user mismatch | local_user=" + normalized_local_user + " | machine_username=" + machine_username + " | machine_name=" + machine_name_value)
            return Response({"detail": "设备账号与本机用户名不匹配", "debug_step": "local_user_mismatch"}, status=status.HTTP_403_FORBIDDEN)

        login_name = normalized_local_user or machine_username
        if not login_name:
            device_login_debug("ERROR STEP 4 empty login_name")
            return Response({"detail": "设备未绑定登录账号", "debug_step": "empty_login_name"}, status=status.HTTP_400_BAD_REQUEST)
        device_login_debug("STEP 4 login user resolved | login_name=" + login_name)

        User = get_user_model()
        user = User.objects.filter(username__iexact=login_name).first()
        if not user or not user.is_active:
            device_login_debug("ERROR STEP 5 user missing or inactive | login_name=" + login_name)
            return Response({"detail": "设备账号不存在或已禁用", "debug_step": "user_missing_or_inactive"}, status=status.HTTP_403_FORBIDDEN)
        device_login_debug("STEP 5 user found | username=" + user.username)

        if not has_device_secret:
            try:
                is_land_host = user.roles.filter(name='land设备主机').exists()
            except AttributeError:
                is_land_host = False
            if not is_land_host:
                device_login_debug("ERROR STEP 6 user is not land host | username=" + user.username)
                return Response({"detail": "免密设备登录仅限 land 设备主机账号", "debug_step": "not_land_host"}, status=status.HTTP_403_FORBIDDEN)
            device_login_debug("STEP 6 land host role verified")

        refresh = RefreshToken.for_user(user)
        device_login_debug("STEP 7 token issued | username=" + user.username)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user_id": user.id,
            "username": user.username
        })

class RdpMachineViewSet(viewsets.ModelViewSet):
    serializer_class = RdpMachineSerializer
    permission_classes = [IsSystemAdminOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if check_is_system_admin(user):
            return RdpMachine.objects.all().order_by('name')
        return RdpMachine.objects.filter(is_active=True).order_by('name')

    @action(detail=True, methods=['get'])
    def current_status(self, request, pk=None):
        machine = self.get_object()
        now = timezone.now()

        current_booking = None
        candidate_bookings = RdpBooking.objects.filter(
            machine=machine,
            status__in=['confirmed', 'active'],
            start_time__lte=now
        ).select_related('user', 'takeover_applicant').order_by('start_time')

        for candidate in candidate_bookings:
            if advance_remote_booking_state(candidate, now):
                continue
            if get_booking_effective_end_time(candidate) > now:
                current_booking = candidate
                break

        if current_booking:
            display_name = get_user_display_name(current_booking.user)
            effective_end_time = get_booking_effective_end_time(current_booking)
            return Response({
                "status": "occupied",
                "booking_id": current_booking.id,
                "user": display_name,
                "start_time": current_booking.start_time,
                "end_time": effective_end_time,
                "is_self_booking": current_booking.user == request.user,
                "is_takeover_pending": (
                        current_booking.takeover_status == 'pending' and
                        current_booking.takeover_applicant == request.user
                ),
                "takeover_rejected_cooldown_seconds": TAKEOVER_REJECTED_COOLDOWN_SECONDS,
                "takeover_rejected_cooldown_remaining_seconds": get_takeover_rejected_cooldown_remaining_seconds(
                    current_booking, request.user, now
                ),
                **build_takeover_status_payload(current_booking, now),
            })
        else:
            return Response({
                "status": "free",
                "message": "当前空闲"
            })


class RdpBookingViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return RdpBooking.objects.filter(user=self.request.user).select_related('machine', 'takeover_applicant')

    def get_serializer_class(self):
        if self.action == 'create':
            return RdpBookingCreateSerializer
        return RdpBookingSerializer

    # --- 标准 CRUD ---

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer_class()(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            booking = serializer.save()
            read_serializer = RdpBookingSerializer(booking)
            return Response(read_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def instant_connect(self, request):
        machine_id = request.data.get('machine')
        now = timezone.now()
        serializer = RdpBookingCreateSerializer(
            data={
                'machine': machine_id,
                'start_time': now.isoformat(),
                'end_time': (now + MAX_REMOTE_BOOKING_DURATION).isoformat(),
            },
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        booking = serializer.save()
        return Response(RdpBookingSerializer(booking).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def my(self, request):
        """
        [终极修复版] 获取“我”的记录。
        通过 Python 层计算北京时间的当日起止点，避开数据库时区转换失效问题。
        """
        queryset = self.get_queryset()
        query_date_str = request.query_params.get('date', None)
        tz = get_current_timezone()  # 获取 settings.py 中的 Asia/Shanghai

        try:
            if query_date_str:
                # 解析前端传来的 YYYY-MM-DD
                target_date = datetime.datetime.strptime(query_date_str, '%Y-%m-%d').date()
            else:
                # 默认获取北京时间的今天
                target_date = timezone.localtime(timezone.now()).date()

            # 构造北京时间当天的 00:00:00 和 23:59:59.999
            start_datetime = make_aware(datetime.datetime.combine(target_date, datetime.time.min), tz)
            end_datetime = make_aware(datetime.datetime.combine(target_date, datetime.time.max), tz)

            # 使用范围查询 (Range)，这在任何数据库环境下都极其稳定
            queryset = queryset.filter(start_time__range=(start_datetime, end_datetime))

        except Exception as e:
            print(f"日期解析或过滤错误: {e}")
            # 如果出错，兜底不进行日期过滤，显示全部（或根据需要修改）
            pass

        # 排序并分页
        queryset = queryset.order_by('-start_time')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        try:
            booking = self.get_object()
        except:
            return Response({"detail": "未找到预约"}, status=status.HTTP_404_NOT_FOUND)

        if booking.status not in ['confirmed']:
            return Response({"detail": "只能取消已确认状态的预约"}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'canceled'
        booking.save()
        return Response(RdpBookingSerializer(booking).data)

    # --- 核心连接与控制逻辑 ---

    @action(detail=True, methods=['post'])
    def connect(self, request, pk=None):
        try:
            booking = self.get_object()
        except:
            return Response({"detail": "预约不存在"}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        if booking.status not in ['confirmed', 'active']:
            return Response({"detail": "预约状态无效"}, status=status.HTTP_403_FORBIDDEN)

        terminal_reason = advance_remote_booking_state(booking, now)
        if terminal_reason:
            message = "超时未响应插队申请" if terminal_reason == 'takeover_timeout' else "预约已超过 30 分钟上限"
            return Response({"detail": message}, status=status.HTTP_403_FORBIDDEN)

        effective_end_time = get_booking_effective_end_time(booking)
        if not (booking.start_time - timezone.timedelta(minutes=5) <= now < effective_end_time):
            return Response({"detail": "未在允许的预约时间段内"}, status=status.HTTP_403_FORBIDDEN)

        machine = booking.machine
        auth_token = None
        guac_session, guac_api_url, auth_token = get_guacamole_auth_context()

        real_guacamole_id = None
        if auth_token:
            try:
                real_guacamole_id = find_guacamole_connection_identifier(
                    machine,
                    guac_session,
                    guac_api_url,
                    auth_token,
                    allow_model_fallback=False
                )
            except:
                pass

        if not real_guacamole_id:
            guac_session, guac_api_url, auth_token = get_guacamole_auth_context(force_refresh=True)
            if auth_token:
                try:
                    real_guacamole_id = find_guacamole_connection_identifier(
                        machine,
                        guac_session,
                        guac_api_url,
                        auth_token,
                        allow_model_fallback=False
                    )
                except:
                    pass

        if not real_guacamole_id:
            return Response({"detail": "在 Guacamole 中找不到匹配的连接"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        raw_id = f"{real_guacamole_id}\0c\0{GUAC_AUTH_PROVIDER}"
        client_identifier = base64.b64encode(raw_id.encode('utf-8')).decode('utf-8')
        final_url = f"{GUACAMOLE_URL}/#/client/{client_identifier}"
        if auth_token: final_url += f"?token={auth_token}"

        if booking.status == 'confirmed':
            booking.status = 'active'
            booking.save()

        return Response({"message": "连接就绪", "connection_url": final_url})

    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        try:
            booking = self.get_object()
        except RdpBooking.DoesNotExist:
            return Response({"detail": "预约不存在"}, status=status.HTTP_404_NOT_FOUND)

        try:
            if booking.status in ['completed', 'canceled']:
                return Response({"detail": "已登出"})
            booking.status = 'completed'
            booking.real_end_time = timezone.now()
            booking.termination_reason = 'normal'
            booking.save()
            disconnect_guacamole_active_connections_for_booking(booking, 'normal_disconnect')
            return Response({"detail": "已登出"})
        except Exception:
            return Response({"detail": "状态更新失败"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def request_takeover(self, request, pk=None):
        try:
            target_booking = RdpBooking.objects.get(pk=pk)
        except RdpBooking.DoesNotExist:
            return Response({"detail": "预约不存在"}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        if target_booking.status in ['completed', 'canceled']:
            return Response({"detail": "该预约已结束"}, status=status.HTTP_400_BAD_REQUEST)
        terminal_reason = advance_remote_booking_state(target_booking, now)
        if terminal_reason:
            message = "插队申请已超时处理，该预约已结束" if terminal_reason == 'takeover_timeout' else "该预约已超过 30 分钟上限"
            return Response({"detail": message}, status=status.HTTP_400_BAD_REQUEST)

        cooldown_remaining = get_takeover_rejected_cooldown_remaining_seconds(target_booking, request.user, now)
        if cooldown_remaining > 0:
            return Response({
                "detail": "对方已拒绝，请稍后再次申请",
                "takeover_rejected_cooldown_seconds": TAKEOVER_REJECTED_COOLDOWN_SECONDS,
                "takeover_rejected_cooldown_remaining_seconds": cooldown_remaining,
            }, status=status.HTTP_429_TOO_MANY_REQUESTS)

        target_booking.takeover_applicant = request.user
        target_booking.takeover_requested_at = now
        target_booking.takeover_status = 'pending'
        target_booking.save()
        return Response({
            "detail": "插队申请已发送",
            **build_takeover_status_payload(target_booking, now),
        })

    @action(detail=True, methods=['post'])
    def approve_takeover(self, request, pk=None):
        booking = self.get_object()
        if booking.takeover_status != 'pending':
            return Response({"detail": "没有待处理的申请"}, status=status.HTTP_400_BAD_REQUEST)

        booking.status = 'completed'
        booking.real_end_time = timezone.now()
        booking.termination_reason = 'takeover'
        booking.takeover_status = 'approved'
        booking.save()
        disconnect_guacamole_active_connections_for_booking(booking, 'takeover_approved')
        return Response({"detail": "已同意"})

    @action(detail=True, methods=['post'])
    def reject_takeover(self, request, pk=None):
        booking = self.get_object()
        if booking.takeover_status != 'pending':
            return Response({"detail": "没有待处理的申请"}, status=status.HTTP_400_BAD_REQUEST)
        booking.takeover_status = 'rejected'
        booking.save()
        return Response({"detail": "已拒绝申请"})

    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        try:
            booking = self.get_object()
        except:
            return Response({"status": "force_disconnected", "message": "预约已失效"})

        now = timezone.now()
        if booking.status in ['completed', 'canceled']:
            return Response({"status": "force_disconnected", "message": "会话已结束"})

        terminal_reason = advance_remote_booking_state(booking, now)
        if terminal_reason == 'takeover_timeout':
            return Response(
                {"status": "force_disconnected", "reason": "takeover_timeout", "message": "超时未响应插队申请"})
        if terminal_reason == 'time_up':
            return Response({"status": "force_disconnected", "reason": "time_up", "message": "时间已到，单次远程连接最长 30 分钟"})

        effective_end_time = get_booking_effective_end_time(booking)
        remaining_seconds = (effective_end_time - now).total_seconds()
        if remaining_seconds <= 0:
            complete_expired_remote_booking(booking, now)
            return Response({"status": "force_disconnected", "reason": "time_up", "message": "时间已到，单次远程连接最长 30 分钟"})

        applicant_name = get_user_display_name(booking.takeover_applicant)
        return Response({
            "status": booking.status,
            "remaining_seconds": remaining_seconds,
            "takeover_request": {
                "has_request": booking.takeover_status == 'pending',
                "applicant_name": applicant_name,
                "request_time": booking.takeover_requested_at,
                "timeout_seconds": TAKEOVER_TIMEOUT_SECONDS,
                "remaining_seconds": get_takeover_remaining_seconds(booking, now),
                "expires_at": (
                    booking.takeover_requested_at + timezone.timedelta(seconds=TAKEOVER_TIMEOUT_SECONDS)
                    if booking.takeover_requested_at else None
                ),
            }
        })
