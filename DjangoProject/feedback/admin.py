from django.contrib import admin

from .models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "created_at", "replied_at", "replied_by")
    list_filter = ("category", "created_at", "replied_at")
    search_fields = ("content", "admin_reply")
    readonly_fields = ("created_at", "updated_at", "replied_by", "replied_at")
