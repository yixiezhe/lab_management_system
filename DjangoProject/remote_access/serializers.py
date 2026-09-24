from rest_framework import serializers
from .models import RdpMachine, RdpBooking, MAX_REMOTE_BOOKING_DURATION, get_remote_booking_effective_end_time
from users.serializers import UserProfileSerializer
from django.utils import timezone
from django.db.models import Q



class RdpMachineSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={'input_type': 'password'}
    )
    device_secret = serializers.CharField(
        write_only=True, required=False, allow_blank=True, style={'input_type': 'password'}
    )
    has_device_secret = serializers.SerializerMethodField()

    class Meta:
        model = RdpMachine
        fields = (
            'id',
            'name',
            'ip_address',
            'guacamole_id',  # [新增] 允许读写 Guacamole ID
            'description',
            'is_active',
            'username',
            'password',
            'device_secret',
            'has_device_secret'
        )

    def create(self, validated_data):
        raw_password = validated_data.pop('password', None)
        raw_secret = validated_data.pop('device_secret', None)
        machine = RdpMachine.objects.create(**validated_data)
        if raw_password:
            machine.password = raw_password
        if raw_secret is not None:
            machine.set_device_secret(raw_secret)
        if raw_password or raw_secret is not None:
            machine.save()
        return machine

    def update(self, instance, validated_data):
        raw_password = validated_data.pop('password', None)
        raw_secret = validated_data.pop('device_secret', None)
        if raw_password:
            instance.password = raw_password
        if raw_secret is not None:
            instance.set_device_secret(raw_secret)
        super().update(instance, validated_data)
        return instance

    def get_has_device_secret(self, obj):
        return bool(obj.device_secret_hash or obj.encrypted_device_secret)


class RdpBookingSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    machine = RdpMachineSerializer(read_only=True)
    takeover_applicant = UserProfileSerializer(read_only=True)

    class Meta:
        model = RdpBooking
        fields = (
            'id', 'user', 'machine', 'start_time', 'end_time', 'status', 'created_at',
            'real_end_time', 'termination_reason', 'takeover_applicant',
            'takeover_requested_at', 'takeover_status',
        )
        read_only_fields = fields


class RdpBookingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RdpBooking
        fields = ('machine', 'start_time', 'end_time')
        extra_kwargs = {
            'machine': {'queryset': RdpMachine.objects.filter(is_active=True)}
        }

    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        machine = attrs.get('machine')

        if start_time >= end_time:
            raise serializers.ValidationError("结束时间必须晚于开始时间")

        if end_time - start_time > MAX_REMOTE_BOOKING_DURATION:
            raise serializers.ValidationError("单次远程连接最长 30 分钟")

        # 允许稍微早一点的预约，或者基于当前时间
        # if start_time < (timezone.now() - timezone.timedelta(minutes=5)): ...

        effective_end_time = get_remote_booking_effective_end_time(start_time, end_time)
        overlapping_bookings = RdpBooking.objects.filter(
            Q(start_time__lt=effective_end_time) & Q(end_time__gt=start_time),
            machine=machine,
            status__in=['confirmed', 'active']
        )

        for booking in overlapping_bookings:
            if booking.effective_end_time > start_time:
                raise serializers.ValidationError(f"资源冲突：主机 {machine.name} 在该时间段已被预约")

        attrs['user'] = self.context['request'].user
        return attrs

    def create(self, validated_data):
        return RdpBooking.objects.create(**validated_data)


class DeviceLoginSerializer(serializers.Serializer):
    machine_id = serializers.IntegerField(required=False)
    machine_name = serializers.CharField(required=False)
    local_user = serializers.CharField(required=False)
    device_secret = serializers.CharField(required=False, allow_blank=True)
