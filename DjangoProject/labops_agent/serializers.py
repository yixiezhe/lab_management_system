from decimal import Decimal

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    """Reject model-invented fields instead of silently ignoring them."""

    def to_internal_value(self, data):
        if not isinstance(data, dict):
            raise serializers.ValidationError("工具参数必须是 JSON 对象。")
        unknown = sorted(set(data) - set(self.fields))
        if unknown:
            raise serializers.ValidationError(
                {"unknown_fields": [f"不支持的参数：{', '.join(unknown)}"]}
            )
        return super().to_internal_value(data)


class AgentQuerySerializer(serializers.Serializer):
    question = serializers.CharField(
        max_length=1000,
        allow_blank=False,
        trim_whitespace=True,
    )
    history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        max_length=8,
    )
    conversation_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_history(self, value):
        cleaned = []
        total_length = 0
        for item in value:
            if set(item) != {"role", "content"}:
                raise serializers.ValidationError("历史消息仅支持 role 和 content。")
            role = item.get("role")
            content = str(item.get("content") or "").strip()
            if role not in {"user", "assistant"} or not content:
                raise serializers.ValidationError("历史消息格式无效。")
            if len(content) > 1000:
                raise serializers.ValidationError("单条历史消息不能超过 1000 字。")
            total_length += len(content)
            cleaned.append({"role": role, "content": content})
        if total_length > 5000:
            raise serializers.ValidationError("历史消息总长度不能超过 5000 字。")
        return cleaned


class ProcurementListArgs(StrictSerializer):
    expense_type = serializers.ChoiceField(
        choices=("public", "c2c"), required=False, allow_null=True
    )
    statuses = serializers.ListField(
        child=serializers.CharField(max_length=40),
        required=False,
        allow_null=True,
        max_length=12,
    )
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20)


class ProcurementDetailArgs(StrictSerializer):
    request_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    order_number = serializers.CharField(
        required=False, allow_null=True, allow_blank=False, max_length=100
    )

    def validate(self, attrs):
        supplied = [
            attrs.get("request_id") is not None,
            attrs.get("order_number") is not None,
        ]
        if sum(supplied) != 1:
            raise serializers.ValidationError(
                "request_id 和 order_number 必须且只能提供一个。"
            )
        return attrs


class ProcurementDraftItemArgs(StrictSerializer):
    content = serializers.CharField(allow_null=True, allow_blank=True, max_length=200)
    purchase_type = serializers.ChoiceField(
        choices=("consumable", "chemical", "other"), allow_null=True
    )
    manufacturer = serializers.CharField(allow_null=True, allow_blank=True, max_length=200)
    parameters = serializers.CharField(allow_null=True, allow_blank=True, max_length=200)
    cas_number = serializers.CharField(allow_null=True, allow_blank=True, max_length=50)
    product_number = serializers.CharField(allow_null=True, allow_blank=True, max_length=50)
    purchase_link = serializers.CharField(allow_null=True, allow_blank=True, max_length=2000)
    specifications = serializers.CharField(allow_null=True, allow_blank=True, max_length=200)
    unit_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
        allow_null=True,
    )
    quantity = serializers.IntegerField(min_value=1, allow_null=True)


class ProcurementDraftArgs(StrictSerializer):
    expense_type = serializers.ChoiceField(
        choices=("public", "c2c"), allow_null=True
    )
    platform = serializers.CharField(allow_null=True, allow_blank=True, max_length=100)
    items = ProcurementDraftItemArgs(many=True, min_length=1, max_length=10)


class EquipmentSearchArgs(StrictSerializer):
    query = serializers.CharField(required=False, allow_blank=True, max_length=100)
    active_only = serializers.BooleanField(required=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20)


class EquipmentReservationDraftArgs(StrictSerializer):
    equipment_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    equipment_query = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=False,
        max_length=100,
    )
    target_date = serializers.DateField()
    start_time = serializers.TimeField()
    end_time = serializers.TimeField(required=False, allow_null=True)
    duration_minutes = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=24 * 60,
    )
    position_no = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate(self, attrs):
        if attrs.get("equipment_id") is None and not attrs.get("equipment_query"):
            raise serializers.ValidationError("equipment_id 和 equipment_query 至少提供一个。")
        if attrs.get("end_time") is None and attrs.get("duration_minutes") is None:
            raise serializers.ValidationError("end_time 和 duration_minutes 至少提供一个。")
        return attrs


class MyReservationsArgs(StrictSerializer):
    upcoming = serializers.BooleanField(required=False, allow_null=True)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    statuses = serializers.ListField(
        child=serializers.CharField(max_length=40),
        required=False,
        allow_null=True,
        max_length=12,
    )
    limit = serializers.IntegerField(required=False, min_value=1, max_value=30)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date 不能晚于 end_date。")
        return attrs


class AvailableSlotsArgs(StrictSerializer):
    equipment_id = serializers.IntegerField(min_value=1)
    target_date = serializers.DateField()
    position_no = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    rotation_speed_rpm = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )


class ReservationConflictArgs(StrictSerializer):
    equipment_id = serializers.IntegerField(min_value=1)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()
    position_no = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    rotation_speed_rpm = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )

    def validate(self, attrs):
        if attrs["start_at"] >= attrs["end_at"]:
            raise serializers.ValidationError("start_at 必须早于 end_at。")
        return attrs
