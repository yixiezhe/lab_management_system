from django.db import models
from users.models import UserProfile


class Project(models.Model):
    project_number = models.CharField(max_length=50, unique=True, verbose_name="项目号")
    name = models.CharField(max_length=200, verbose_name="项目名")
    description = models.TextField(blank=True, verbose_name="项目说明/公告")
    is_published = models.BooleanField(default=False, verbose_name="发布到首页")

    author = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="创建/修改人"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.project_number} - {self.name}"

    class Meta:
        verbose_name = "项目管理"
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']