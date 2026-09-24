from django.conf import settings
from django.db import models


class Feedback(models.Model):
    CATEGORY_BUG = "bug"
    CATEGORY_SUGGESTION = "suggestion"
    CATEGORY_OTHER = "other"

    CATEGORY_CHOICES = [
        (CATEGORY_BUG, "系统 Bug"),
        (CATEGORY_SUGGESTION, "功能建议"),
        (CATEGORY_OTHER, "其他反馈"),
    ]

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_BUG,
        verbose_name="反馈类型",
    )
    content = models.TextField(verbose_name="反馈内容")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="提交时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    admin_reply = models.TextField(blank=True, default="", verbose_name="管理员回复")
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback_replies",
        verbose_name="回复管理员",
    )
    replied_at = models.DateTimeField(null=True, blank=True, verbose_name="回复时间")

    class Meta:
        verbose_name = "反馈和建议"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_category_display()} #{self.pk}"
