# equipment/admin.py
from django.contrib import admin
from .models import Equipment, Booking, BallMillQueueRequest

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        "name", "booking_mode", "location", "time_unit_minutes",
        "open_time_start", "open_time_end",
        "max_advance_days", "ball_mill_queue_enabled", "is_active",
    )
    list_filter = ("booking_mode", "is_active",)
    search_fields = ("name", "location")

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "equipment",
        "user",
        "date",
        "start_time",
        "end_time",
        "position_no",
        "rotation_speed_rpm",
        "status",
        "created_at",
    )
    list_filter = ("status", "date", "equipment", "operation_type")
    search_fields = ("equipment__name", "user__name")


@admin.register(BallMillQueueRequest)
class BallMillQueueRequestAdmin(admin.ModelAdmin):
    list_display = (
        "equipment",
        "user",
        "requested_date",
        "requested_start_time",
        "position_count",
        "rotation_speed_rpm",
        "status",
        "created_at",
        "dispatched_at",
    )
    list_filter = ("status", "equipment", "operation_type", "requested_date")
    search_fields = ("equipment__name", "user__name", "user__username")
