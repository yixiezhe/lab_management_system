from datetime import date, datetime, time

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from equipment.models import Booking, Equipment
from equipment.services import EquipmentQueryService
from equipment.time_control import clear_test_now, set_test_now
from users.models import Role, UserProfile


class EquipmentQueryServiceTests(TestCase):
    def setUp(self):
        self.land_role = Role.objects.create(name="land设备主机")
        self.user = self.create_user("query_user", "查询用户")
        self.other = self.create_user("query_other", "其他用户")
        self.land_host = self.create_user("query_land", "设备主机")
        self.land_host.roles.add(self.land_role)

        self.standard = Equipment.objects.create(
            name="标准测试仪器",
            location="A101",
            time_unit_minutes=60,
            open_time_start=time(8, 0),
            open_time_end=time(12, 0),
            max_advance_days=7,
        )
        self.restricted = Equipment.objects.create(
            name="受限测试仪器",
            time_unit_minutes=60,
            open_time_start=time(8, 0),
            open_time_end=time(12, 0),
        )
        self.restricted.booking_allowed_users.add(self.other)
        self.inactive = Equipment.objects.create(name="停用测试仪器", is_active=False)

        set_test_now(datetime(2026, 9, 1, 8, 0))
        self.target_date = date(2026, 9, 2)

    def tearDown(self):
        clear_test_now()

    @staticmethod
    def create_user(username, name):
        return UserProfile.objects.create_user(
            username=username,
            password="test-pass-123",
            name=name,
            email=f"{username}@example.com",
        )

    def create_booking(
        self,
        *,
        equipment=None,
        user=None,
        start=time(9, 0),
        end=time(10, 0),
        position_no=None,
    ):
        return Booking.objects.create(
            equipment=equipment or self.standard,
            user=user or self.other,
            date=self.target_date,
            start_time=start,
            end_time=end,
            position_no=position_no,
            status="active",
        )

    def test_search_only_returns_active_allowed_equipment(self):
        rows = EquipmentQueryService.search_equipment(self.user, query="测试")
        self.assertEqual([row["id"] for row in rows], [self.standard.id])

    def test_restricted_equipment_is_not_queryable(self):
        with self.assertRaises(PermissionDenied):
            EquipmentQueryService.get_available_slots(
                self.user,
                equipment_id=self.restricted.id,
                target_date=self.target_date,
            )

    def test_land_host_is_rejected(self):
        with self.assertRaises(PermissionDenied):
            EquipmentQueryService.search_equipment(self.land_host)

    def test_my_reservations_never_returns_other_users_rows(self):
        mine = self.create_booking(user=self.user)
        self.create_booking(user=self.other, start=time(10, 0), end=time(11, 0))

        rows = EquipmentQueryService.get_my_reservations(
            self.user,
            upcoming=True,
            statuses=["active"],
        )
        self.assertEqual([row["id"] for row in rows], [mine.id])

    def test_available_slots_mark_overlap_without_exposing_booker(self):
        self.create_booking()

        result = EquipmentQueryService.get_available_slots(
            self.user,
            equipment_id=self.standard.id,
            target_date=self.target_date,
        )
        slots = {slot["start"]: slot for slot in result["slots"]}
        self.assertTrue(slots["08:00"]["available"])
        self.assertFalse(slots["09:00"]["available"])
        self.assertEqual(slots["09:00"]["reason"], "occupied")
        self.assertNotIn("booked_by", slots["09:00"])

    def test_conflict_detection_treats_touching_boundaries_as_available(self):
        self.create_booking()
        tz = timezone.get_current_timezone()

        overlap = EquipmentQueryService.check_reservation_conflict(
            self.user,
            equipment_id=self.standard.id,
            start_at=timezone.make_aware(datetime(2026, 9, 2, 9, 30), tz),
            end_at=timezone.make_aware(datetime(2026, 9, 2, 10, 30), tz),
        )
        adjacent = EquipmentQueryService.check_reservation_conflict(
            self.user,
            equipment_id=self.standard.id,
            start_at=timezone.make_aware(datetime(2026, 9, 2, 10, 0), tz),
            end_at=timezone.make_aware(datetime(2026, 9, 2, 11, 0), tz),
        )

        self.assertTrue(overlap["conflict"])
        self.assertFalse(adjacent["conflict"])

    def test_electrochemical_slots_report_available_channels(self):
        station = Equipment.objects.create(
            name="电化学测试仪器",
            booking_mode=Equipment.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION,
            time_unit_minutes=60,
            electrochemical_offline_channels=[8],
        )
        self.create_booking(equipment=station, position_no=1)

        result = EquipmentQueryService.get_available_slots(
            self.user,
            equipment_id=station.id,
            target_date=self.target_date,
        )
        slot = next(item for item in result["slots"] if item["start"] == "09:00")
        self.assertTrue(slot["available"])
        self.assertNotIn(1, slot["available_positions"])
        self.assertNotIn(8, slot["available_positions"])
