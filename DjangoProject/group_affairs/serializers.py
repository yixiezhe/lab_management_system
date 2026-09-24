from rest_framework import serializers

from users.models import UserProfile

from .models import GroupAffairAdmin, GroupAffairBoard, GroupAffairNotice, GroupPurchase, default_duty_schedule
from .services import can_manage_board, get_group_members_queryset


WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class GroupAffairUserSerializer(serializers.ModelSerializer):
    assigned_tutor_id = serializers.IntegerField(read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ["id", "username", "name", "email", "roles", "assigned_tutor_id"]

    def get_roles(self, obj):
        return [{"name": name} for name in obj.roles.values_list("name", flat=True)]


class GroupAffairAdminEntrySerializer(serializers.ModelSerializer):
    user = GroupAffairUserSerializer(read_only=True)
    assigned_by = GroupAffairUserSerializer(read_only=True)
    is_default = serializers.SerializerMethodField()

    class Meta:
        model = GroupAffairAdmin
        fields = ["id", "user", "assigned_by", "created_at", "is_default"]

    def get_is_default(self, obj):
        return False


class GroupAffairBoardSerializer(serializers.ModelSerializer):
    tutor = GroupAffairUserSerializer(read_only=True)
    updated_by = GroupAffairUserSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = GroupAffairBoard
        fields = [
            "id",
            "tutor",
            "text_content",
            "duty_schedule",
            "duty_reminder_enabled",
            "purchase_rotation",
            "purchase_rotation_index",
            "updated_by",
            "updated_at",
            "members",
            "admins",
            "can_manage",
        ]
        read_only_fields = ["id", "tutor", "purchase_rotation_index", "updated_by", "updated_at", "members", "admins", "can_manage"]

    def get_members(self, obj):
        return GroupAffairUserSerializer(get_group_members_queryset(obj.tutor), many=True).data

    def get_admins(self, obj):
        default_admin = {
            "id": None,
            "user": GroupAffairUserSerializer(obj.tutor).data,
            "assigned_by": None,
            "created_at": None,
            "is_default": True,
        }
        extra_admins = (
            GroupAffairAdmin.objects
            .filter(tutor=obj.tutor)
            .exclude(user=obj.tutor)
            .select_related("user", "assigned_by")
            .order_by("user__name", "user__username", "id")
        )
        data = [default_admin]
        data.extend(GroupAffairAdminEntrySerializer(extra_admins, many=True).data)
        return data

    def get_can_manage(self, obj):
        request = self.context.get("request")
        return can_manage_board(getattr(request, "user", None), obj)

    def validate_duty_schedule(self, value):
        if value in (None, ""):
            return default_duty_schedule()
        if not isinstance(value, list):
            raise serializers.ValidationError("值日表必须是数组。")

        weekday_to_user_id = {i: None for i in range(7)}
        seen_weekdays = set()
        selected_user_ids = set()

        for idx, item in enumerate(value):
            if not isinstance(item, dict):
                raise serializers.ValidationError(f"第 {idx + 1} 项必须是对象。")
            try:
                weekday = int(item.get("weekday"))
            except (TypeError, ValueError):
                raise serializers.ValidationError(f"第 {idx + 1} 项的 weekday 必须是 0-6 的整数。")
            if weekday < 0 or weekday > 6:
                raise serializers.ValidationError(f"第 {idx + 1} 项的 weekday 超出范围（0-6）。")
            if weekday in seen_weekdays:
                raise serializers.ValidationError(f"weekday={weekday} 重复，请保证每个星期只出现一次。")
            seen_weekdays.add(weekday)

            raw_user_id = item.get("user_id")
            if raw_user_id in (None, ""):
                user_id = None
            else:
                try:
                    user_id = int(raw_user_id)
                except (TypeError, ValueError):
                    raise serializers.ValidationError(f"{WEEKDAY_LABELS[weekday]} 的值日人员无效。")
                selected_user_ids.add(user_id)
            weekday_to_user_id[weekday] = user_id

        if self.instance and selected_user_ids:
            allowed_user_ids = set(get_group_members_queryset(self.instance.tutor).values_list("id", flat=True))
            invalid_user_ids = selected_user_ids - allowed_user_ids
            if invalid_user_ids:
                raise serializers.ValidationError("值日人员必须是本小组成员。")

        return [
            {"weekday": weekday, "user_id": weekday_to_user_id[weekday], "name": ""}
            for weekday in range(7)
        ]

    def validate_purchase_rotation(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("采购轮班名单必须是数组。")
        try:
            user_ids = [int(item) for item in value]
        except (TypeError, ValueError):
            raise serializers.ValidationError("采购轮班名单包含无效成员。")
        if len(user_ids) != len(set(user_ids)):
            raise serializers.ValidationError("采购轮班名单不能包含重复成员。")
        if self.instance and user_ids:
            allowed = set(get_group_members_queryset(self.instance.tutor).values_list("id", flat=True))
            if set(user_ids) - allowed:
                raise serializers.ValidationError("采购轮班人员必须是本小组成员。")
        return user_ids

    def to_representation(self, instance):
        data = super().to_representation(instance)
        schedule = data.get("duty_schedule") or default_duty_schedule()
        user_ids = [
            item.get("user_id")
            for item in schedule
            if isinstance(item, dict) and item.get("user_id")
        ]
        user_map = {
            user.id: user
            for user in UserProfile.objects.filter(id__in=user_ids)
        }

        weekday_to_item = {i: {"weekday": i, "user_id": None, "name": ""} for i in range(7)}
        for item in schedule:
            if not isinstance(item, dict):
                continue
            try:
                weekday = int(item.get("weekday"))
            except (TypeError, ValueError):
                continue
            if weekday < 0 or weekday > 6:
                continue
            raw_user_id = item.get("user_id")
            user_id = int(raw_user_id) if raw_user_id else None
            user = user_map.get(user_id)
            weekday_to_item[weekday] = {
                "weekday": weekday,
                "weekday_label": WEEKDAY_LABELS[weekday],
                "user_id": user_id,
                "name": user.name if user else "",
            }

        data["duty_schedule"] = [weekday_to_item[i] for i in range(7)]
        return data


class GroupAffairNoticeSerializer(serializers.ModelSerializer):
    board = serializers.PrimaryKeyRelatedField(read_only=True)
    board_tutor_name = serializers.CharField(source="board.tutor.name", read_only=True)
    created_by = GroupAffairUserSerializer(read_only=True)

    class Meta:
        model = GroupAffairNotice
        fields = ["id", "board", "board_tutor_name", "title", "content", "created_by", "created_at"]
        read_only_fields = ["id", "board", "board_tutor_name", "created_by", "created_at"]

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("请填写提醒标题。")
        return value

    def validate_content(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("请填写提醒内容。")
        return value


class GroupPurchaseSerializer(serializers.ModelSerializer):
    requester = GroupAffairUserSerializer(read_only=True)
    buyer = GroupAffairUserSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    payment_proof = serializers.SerializerMethodField()
    invoice = serializers.SerializerMethodField()
    item_image = serializers.SerializerMethodField()

    class Meta:
        model = GroupPurchase
        fields = [
            "id", "board", "requester", "buyer", "items", "note", "status", "status_display",
            "payment_amount", "payment_proof", "invoice", "item_image", "paid_at", "arrived_at",
            "reimbursed_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "board", "requester", "buyer", "status", "status_display", "payment_amount",
            "payment_proof", "invoice", "item_image", "paid_at", "arrived_at", "reimbursed_at",
            "created_at", "updated_at",
        ]

    def validate_items(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("请填写要购买的物品。")
        return value

    @staticmethod
    def _relative_file_url(file_field):
        if not file_field:
            return None
        return file_field.url

    def get_payment_proof(self, obj):
        return self._relative_file_url(obj.payment_proof)

    def get_invoice(self, obj):
        return self._relative_file_url(obj.invoice)

    def get_item_image(self, obj):
        return self._relative_file_url(obj.item_image)
