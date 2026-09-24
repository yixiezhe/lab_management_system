from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password
import pytz
from django.utils import timezone


MAX_REMOTE_BOOKING_DURATION = timezone.timedelta(minutes=30)


def get_remote_booking_effective_end_time(start_time, end_time):
    return min(end_time, start_time + MAX_REMOTE_BOOKING_DURATION)

# 1. 加密工具
try:
    fernet_key = settings.FERNET_KEY.encode()
    cipher_suite = Fernet(fernet_key)
except Exception as e:
    raise RuntimeError(f"FERNET_KEY 在 settings.py 中配置错误或缺失: {e}")


def encrypt_password(password):
    if not password: return ""
    return cipher_suite.encrypt(password.encode()).decode()


def decrypt_password(encrypted_password):
    if not encrypted_password: return ""
    try:
        return cipher_suite.decrypt(encrypted_password.encode()).decode()
    except Exception:
        return "DECRYPTION_ERROR"


# 2. 目标主机模型
class RdpMachine(models.Model):
    """存储目标 Windows 主机"""
    name = models.CharField(max_length=100, unique=True, verbose_name="主机名称")
    ip_address = models.CharField(max_length=100, verbose_name="IP 地址或域名")
    description = models.TextField(blank=True, null=True, verbose_name="主机描述")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")

    # --- [新增] Guacamole 连接 ID ---
    # 这个 ID 需要您去 Guacamole 网页的 URL 里看，或者数据库里查
    # 默认为 1，防止报错
    guacamole_id = models.IntegerField(default=1, verbose_name="Guacamole连接ID", help_text="请对应 Guacamole 设置中的连接 ID")

    # 账户信息
    username = models.CharField(max_length=100, verbose_name="Windows 用户名", blank=True)
    encrypted_password = models.CharField(max_length=500, verbose_name="加密后的密码", blank=True)
    device_secret_hash = models.CharField(max_length=128, verbose_name="设备密钥(哈希)", blank=True)
    encrypted_device_secret = models.CharField(max_length=500, verbose_name="设备密钥(加密)", blank=True)
    device_secret_updated_at = models.DateTimeField(null=True, blank=True, verbose_name="密钥更新时间")

    @property
    def password(self):
        return decrypt_password(self.encrypted_password)

    @password.setter
    def password(self, raw_password):
        self.encrypted_password = encrypt_password(raw_password)

    def set_device_secret(self, raw_secret):
        if raw_secret:
            self.device_secret_hash = make_password(raw_secret)
            self.encrypted_device_secret = encrypt_password(raw_secret)
            self.device_secret_updated_at = timezone.now()
        else:
            self.device_secret_hash = ""
            self.encrypted_device_secret = ""
            self.device_secret_updated_at = None

    def verify_device_secret(self, raw_secret):
        if not raw_secret:
            return False
        if self.encrypted_device_secret:
            return decrypt_password(self.encrypted_device_secret) == raw_secret
        if self.device_secret_hash:
            return check_password(raw_secret, self.device_secret_hash)
        return False

    @property
    def device_secret(self):
        if not self.encrypted_device_secret:
            return ""
        return decrypt_password(self.encrypted_device_secret)

    def __str__(self):
        return f"{self.name} (GuacID: {self.guacamole_id})"

    class Meta:
        verbose_name = "远程主机 (含账户)"
        verbose_name_plural = verbose_name


# 3. 预约记录模型
class RdpBooking(models.Model):
    STATUS_CHOICES = [
        ('confirmed', '已确认'),
        ('active', '进行中'),
        ('completed', '已完成'),
        ('canceled', '已取消'),
    ]

    TERMINATION_REASON_CHOICES = [
        ('normal', '主动登出'),
        ('forced', '超时强制断开'),
        ('takeover', '被紧急占用'),
    ]

    TAKEOVER_STATUS_CHOICES = [
        ('none', '无'),
        ('pending', '等待同意'),
        ('approved', '已同意'),
        ('rejected', '已拒绝'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rdp_bookings", verbose_name="预约用户")
    machine = models.ForeignKey(RdpMachine, on_delete=models.CASCADE, related_name="bookings", verbose_name="预约的主机")

    start_time = models.DateTimeField(verbose_name="开始时间")
    end_time = models.DateTimeField(verbose_name="结束时间")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed', verbose_name="预约状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    real_end_time = models.DateTimeField(null=True, blank=True, verbose_name="实际结束时间")
    termination_reason = models.CharField(max_length=20, choices=TERMINATION_REASON_CHOICES, null=True, blank=True, verbose_name="结束原因")

    # 插队信息
    takeover_applicant = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="applied_takeovers", verbose_name="申请插队人")
    takeover_requested_at = models.DateTimeField(null=True, blank=True, verbose_name="申请插队时间")
    takeover_status = models.CharField(max_length=20, choices=TAKEOVER_STATUS_CHOICES, default='none', verbose_name="插队处理状态")

    def __str__(self):
        return f"{self.user.username} 预约 {self.machine.name}"

    @property
    def effective_end_time(self):
        return get_remote_booking_effective_end_time(self.start_time, self.end_time)

    def clean(self):
        super().clean()
        if self.start_time >= self.end_time:
            raise ValidationError("结束时间必须晚于开始时间")

        if self.status not in ['confirmed', 'active']:
            return

        if self.end_time - self.start_time > MAX_REMOTE_BOOKING_DURATION:
            raise ValidationError("单次远程连接最长 30 分钟")

        effective_end_time = self.effective_end_time
        overlapping_bookings = RdpBooking.objects.filter(
            machine=self.machine,
            status__in=['confirmed', 'active'],
            start_time__lt=effective_end_time,
            end_time__gt=self.start_time
        ).exclude(pk=self.pk)

        for booking in overlapping_bookings:
            if booking.effective_end_time > self.start_time:
                raise ValidationError(f"资源冲突：主机 {self.machine.name} 在该时间段已被预约")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "远程预约记录"
        verbose_name_plural = verbose_name
        ordering = ['-start_time']
