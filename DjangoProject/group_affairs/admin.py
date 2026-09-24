from django.contrib import admin

from .models import (
    GroupAffairAdmin,
    GroupAffairBoard,
    GroupAffairDutyReminderRead,
    GroupAffairNotice,
    GroupAffairNoticeRead,
    GroupPurchase,
    GroupPurchasePopupRead,
)


@admin.register(GroupAffairBoard)
class GroupAffairBoardAdmin(admin.ModelAdmin):
    list_display = ("id", "tutor", "duty_reminder_enabled", "updated_by", "updated_at")
    list_filter = ("duty_reminder_enabled",)
    search_fields = ("tutor__name", "tutor__username", "text_content")
    readonly_fields = ("updated_at",)


@admin.register(GroupAffairAdmin)
class GroupAffairAdminAdmin(admin.ModelAdmin):
    list_display = ("id", "tutor", "user", "assigned_by", "created_at")
    list_filter = ("tutor",)
    search_fields = ("tutor__name", "user__name", "user__username")
    readonly_fields = ("created_at",)


@admin.register(GroupAffairNotice)
class GroupAffairNoticeAdmin(admin.ModelAdmin):
    list_display = ("id", "board", "title", "created_by", "created_at")
    list_filter = ("board__tutor", "created_at")
    search_fields = ("title", "content", "board__tutor__name")
    readonly_fields = ("created_at",)


@admin.register(GroupAffairNoticeRead)
class GroupAffairNoticeReadAdmin(admin.ModelAdmin):
    list_display = ("id", "notice", "user", "read_at")
    list_filter = ("read_at",)
    search_fields = ("notice__title", "user__name", "user__username")
    readonly_fields = ("read_at",)


@admin.register(GroupAffairDutyReminderRead)
class GroupAffairDutyReminderReadAdmin(admin.ModelAdmin):
    list_display = ("id", "board", "user", "duty_date", "read_at")
    list_filter = ("duty_date", "board__tutor")
    search_fields = ("board__tutor__name", "user__name", "user__username")
    readonly_fields = ("read_at",)


@admin.register(GroupPurchase)
class GroupPurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "board", "requester", "buyer", "status", "payment_amount", "created_at")
    list_filter = ("status", "board__tutor")
    search_fields = ("items", "requester__name", "buyer__name")
    readonly_fields = ("created_at", "updated_at", "paid_at", "arrived_at", "reimbursed_at")


@admin.register(GroupPurchasePopupRead)
class GroupPurchasePopupReadAdmin(admin.ModelAdmin):
    list_display = ("id", "purchase", "user", "reminder_type", "reminder_date", "read_at")
    list_filter = ("reminder_type", "reminder_date")
    readonly_fields = ("read_at",)
