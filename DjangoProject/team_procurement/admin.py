from django.contrib import admin
from .models import TeamPurchaseRequest, TeamRequestItem


# 使用内联（Inline）的方式，使得物品可以直接在请购申请的详情页中进行编辑
class TeamRequestItemInline(admin.TabularInline):
    model = TeamRequestItem
    extra = 1  # 默认显示1个额外的空行用于添加


@admin.register(TeamPurchaseRequest)
class TeamPurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'applicant', 'tutor', 'request_date', 'total_price', 'status')
    list_filter = ('status', 'tutor', 'request_date')
    search_fields = ('applicant__name', 'tutor__name', 'items__content')
    date_hierarchy = 'request_date'

    # 将物品编辑嵌入到申请详情页中
    inlines = [TeamRequestItemInline]

    # 在详情页中将一些自动计算或关联的字段设为只读
    readonly_fields = ('applicant', 'tutor', 'total_price')

# TeamRequestItem 会通过 TeamRequestItemInline 被管理，无需单独注册
# admin.site.register(TeamRequestItem)