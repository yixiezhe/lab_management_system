from rest_framework import serializers

from .models import Feedback


class FeedbackSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    has_reply = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = [
            "id",
            "category",
            "category_display",
            "content",
            "created_at",
            "updated_at",
            "admin_reply",
            "replied_at",
            "has_reply",
        ]
        read_only_fields = [
            "id",
            "category_display",
            "created_at",
            "updated_at",
            "admin_reply",
            "replied_at",
            "has_reply",
        ]

    def get_has_reply(self, obj):
        return bool((obj.admin_reply or "").strip())

    def validate_content(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("请填写反馈内容。")
        return value


class FeedbackReplySerializer(serializers.Serializer):
    admin_reply = serializers.CharField(allow_blank=False, trim_whitespace=True)

    def validate_admin_reply(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("请填写回复内容。")
        return value
