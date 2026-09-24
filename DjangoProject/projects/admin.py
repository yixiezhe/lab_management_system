from django.contrib import admin
from .models import Project

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    项目管理后台界面自定义
    """
    list_display = ('project_number', 'name', 'author', 'is_published', 'updated_at')
    list_filter = ('is_published',)
    search_fields = ('project_number', 'name', 'description')
    list_editable = ('is_published',)
    readonly_fields = ('created_at', 'updated_at', 'author')

    def save_model(self, request, obj, form, change):
        # 在通过后台首次创建对象时，自动将作者设置为当前登录用户
        if not obj.pk:
            obj.author = request.user
        super().save_model(request, obj, form, change)