import csv
from datetime import date, datetime, time, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Booking, Equipment
from .time_control import clear_test_now, set_test_now


class ElectrochemicalWorkstationBookingTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="electro_user",
            password="pass12345",
            name="电化学用户",
            email="electro@example.com",
        )
        self.admin = user_model.objects.create_superuser(
            username="electro_admin",
            password="pass12345",
            name="电化学管理员",
            email="electro-admin@example.com",
        )
        self.equipment = Equipment.objects.create(
            name="输力强电化学工作站",
            booking_mode=Equipment.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION,
            open_time_start=time(8, 0),
            open_time_end=time(22, 0),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.target_date = date.today() + timedelta(days=1)

    def test_available_slots_include_terminal_hour(self):
        response = self.client.get(
            f"/api/equipment/equipments/{self.equipment.id}/available/",
            {"date": self.target_date.isoformat(), "channel_no": 1},
        )

        self.assertEqual(response.status_code, 200)
        slots = response.data["slots"]
        self.assertEqual(len(slots), 24)
        self.assertEqual(slots[0]["start"], "00:00")
        self.assertEqual(slots[0]["end"], "01:00")
        self.assertEqual(slots[-1]["start"], "23:00")
        self.assertEqual(slots[-1]["end"], "23:59")

    def test_can_book_terminal_hour(self):
        response = self.client.post(
            f"/api/equipment/equipments/{self.equipment.id}/book/",
            {
                "date": self.target_date.isoformat(),
                "start_time": "23:00",
                "end_time": "23:59",
                "position_no": 1,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.start_time.strftime("%H:%M"), "23:00")
        self.assertEqual(booking.end_time.strftime("%H:%M"), "23:59")
        self.assertEqual(booking.position_no, 1)

    def test_available_slots_follow_custom_time_unit(self):
        self.equipment.time_unit_minutes = 30
        self.equipment.save()

        response = self.client.get(
            f"/api/equipment/equipments/{self.equipment.id}/available/",
            {"date": self.target_date.isoformat(), "channel_no": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["time_unit"], 30)
        slots = response.data["slots"]
        self.assertEqual(len(slots), 48)
        self.assertEqual(slots[0]["start"], "00:00")
        self.assertEqual(slots[0]["end"], "00:30")
        self.assertEqual(slots[-1]["start"], "23:30")
        self.assertEqual(slots[-1]["end"], "23:59")

        book_response = self.client.post(
            f"/api/equipment/equipments/{self.equipment.id}/book/",
            {
                "date": self.target_date.isoformat(),
                "start_time": "23:30",
                "end_time": "23:59",
                "position_no": 1,
            },
            format="json",
        )

        self.assertEqual(book_response.status_code, 201, book_response.data)

    def test_admin_can_update_electrochemical_time_unit(self):
        self.client.force_authenticate(self.admin)

        response = self.client.patch(
            f"/api/equipment/equipments/{self.equipment.id}/",
            {
                "name": self.equipment.name,
                "booking_mode": Equipment.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION,
                "time_unit_minutes": 30,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
        self.equipment.refresh_from_db()
        self.assertEqual(self.equipment.time_unit_minutes, 30)
        self.assertEqual(self.equipment.open_time_start.strftime("%H:%M"), "00:00")
        self.assertEqual(self.equipment.open_time_end.strftime("%H:%M"), "23:59")


class ElectrochemicalEarlyEndTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="early_end_user",
            password="pass12345",
            name="提前结束用户",
            email="early-end@example.com",
        )
        self.other_user = user_model.objects.create_user(
            username="early_end_other",
            password="pass12345",
            name="其他用户",
            email="early-end-other@example.com",
        )
        self.admin = user_model.objects.create_superuser(
            username="early_end_admin",
            password="pass12345",
            name="提前结束管理员",
            email="early-end-admin@example.com",
        )
        self.equipment = Equipment.objects.create(
            name="输力强电化学工作站",
            booking_mode=Equipment.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION,
            time_unit_minutes=60,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        set_test_now(datetime(2026, 5, 21, 10, 30))

    def tearDown(self):
        clear_test_now()

    def create_booking(self, **overrides):
        values = {
            "equipment": self.equipment,
            "user": self.user,
            "date": date(2026, 5, 21),
            "start_time": time(10, 0),
            "end_time": time(12, 0),
            "position_no": 1,
            "status": "active",
        }
        values.update(overrides)
        return Booking.objects.create(**values)

    def test_owner_can_end_current_booking_early(self):
        booking = self.create_booking()

        response = self.client.post(f"/api/equipment/bookings/{booking.id}/end-early/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "ended_early")
        booking.refresh_from_db()
        self.assertEqual(booking.status, "active")
        self.assertEqual(timezone.localtime(booking.end_at).strftime("%Y-%m-%d %H:%M:%S"), "2026-05-21 10:30:00")
        self.assertEqual(booking.end_time.strftime("%H:%M:%S"), "10:30:00")
        self.assertEqual(booking.actual_duration_minutes, 30)

        mine_response = self.client.get("/api/equipment/bookings/mine/")
        history_response = self.client.get("/api/equipment/bookings/history/")
        self.assertNotIn(booking.id, [row["id"] for row in mine_response.data])
        self.assertIn(booking.id, [row["id"] for row in history_response.data])

    def test_early_end_releases_later_complete_slots(self):
        booking = self.create_booking()
        end_response = self.client.post(f"/api/equipment/bookings/{booking.id}/end-early/")
        self.assertEqual(end_response.status_code, 200, end_response.data)

        availability_response = self.client.get(
            f"/api/equipment/equipments/{self.equipment.id}/available/",
            {"date": "2026-05-21", "channel_no": 1},
        )
        self.assertEqual(availability_response.status_code, 200, availability_response.data)
        slots_by_start = {slot["start"]: slot for slot in availability_response.data["slots"]}
        self.assertTrue(slots_by_start["10:00"]["occupied"])
        self.assertFalse(slots_by_start["11:00"]["occupied"])

        self.client.force_authenticate(self.other_user)
        booking_response = self.client.post(
            f"/api/equipment/equipments/{self.equipment.id}/book/",
            {
                "date": "2026-05-21",
                "start_time": "11:00",
                "end_time": "12:00",
                "position_no": 1,
            },
            format="json",
        )
        self.assertEqual(booking_response.status_code, 201, booking_response.data)

    def test_cannot_end_booking_before_it_starts_or_twice(self):
        future_booking = self.create_booking(
            start_time=time(11, 0),
            end_time=time(12, 0),
        )
        future_response = self.client.post(
            f"/api/equipment/bookings/{future_booking.id}/end-early/"
        )
        self.assertEqual(future_response.status_code, 400)
        future_booking.refresh_from_db()
        self.assertEqual(future_booking.end_time, time(12, 0))

        current_booking = self.create_booking(position_no=2)
        first_response = self.client.post(
            f"/api/equipment/bookings/{current_booking.id}/end-early/"
        )
        second_response = self.client.post(
            f"/api/equipment/bookings/{current_booking.id}/end-early/"
        )
        self.assertEqual(first_response.status_code, 200, first_response.data)
        self.assertEqual(second_response.status_code, 400)

    def test_cannot_end_booking_at_its_exact_start(self):
        booking = self.create_booking()
        set_test_now(datetime(2026, 5, 21, 10, 0))

        response = self.client.post(f"/api/equipment/bookings/{booking.id}/end-early/")

        self.assertEqual(response.status_code, 400)
        booking.refresh_from_db()
        self.assertEqual(booking.end_time, time(12, 0))
        self.assertEqual(booking.actual_duration_minutes, 120)

    def test_other_users_and_admin_cannot_end_the_booking(self):
        booking = self.create_booking()

        self.client.force_authenticate(self.other_user)
        other_response = self.client.post(f"/api/equipment/bookings/{booking.id}/end-early/")
        self.assertEqual(other_response.status_code, 404)

        self.client.force_authenticate(self.admin)
        admin_response = self.client.post(f"/api/equipment/bookings/{booking.id}/end-early/")
        self.assertEqual(admin_response.status_code, 403)

        booking.refresh_from_db()
        self.assertEqual(booking.end_time, time(12, 0))

    def test_non_electrochemical_booking_cannot_end_early(self):
        standard_equipment = Equipment.objects.create(
            name="普通仪器",
            booking_mode=Equipment.BOOKING_MODE_STANDARD,
            time_unit_minutes=60,
            open_time_start=time(0, 0),
            open_time_end=time(23, 0),
        )
        booking = self.create_booking(equipment=standard_equipment, position_no=None)

        response = self.client.post(f"/api/equipment/bookings/{booking.id}/end-early/")

        self.assertEqual(response.status_code, 400)
        booking.refresh_from_db()
        self.assertEqual(booking.end_time, time(12, 0))


class StandardBookingCurrentSlotTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="standard_user",
            password="pass12345",
            name="普通仪器用户",
            email="standard@example.com",
        )
        self.equipment = Equipment.objects.create(
            name="普通仪器",
            booking_mode=Equipment.BOOKING_MODE_STANDARD,
            time_unit_minutes=60,
            open_time_start=time(0, 0),
            open_time_end=time(23, 0),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        set_test_now(datetime(2026, 5, 21, 15, 55))

    def tearDown(self):
        clear_test_now()

    def test_current_slot_can_be_booked(self):
        response = self.client.post(
            f"/api/equipment/equipments/{self.equipment.id}/book/",
            {
                "date": "2026-05-21",
                "start_time": "15:00",
                "end_time": "16:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.start_time.strftime("%H:%M"), "15:00")
        self.assertEqual(booking.end_time.strftime("%H:%M"), "16:00")

    def test_already_ended_slot_cannot_be_booked(self):
        response = self.client.post(
            f"/api/equipment/equipments/{self.equipment.id}/book/",
            {
                "date": "2026-05-21",
                "start_time": "14:00",
                "end_time": "15:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)


class XrdBookingTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="xrd_user",
            password="pass12345",
            name="XRD用户",
            email="xrd@example.com",
        )
        self.next_user = user_model.objects.create_user(
            username="xrd_next_user",
            password="pass12345",
            name="XRD下一位用户",
            email="xrd-next@example.com",
        )
        self.equipment = Equipment.objects.create(
            name="XRD",
            booking_mode=Equipment.BOOKING_MODE_XRD,
            time_unit_minutes=30,
            open_time_start=time(18, 0),
            open_time_end=time(22, 0),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        set_test_now(datetime(2026, 5, 21, 19, 5))

    def tearDown(self):
        clear_test_now()

    def test_xrd_current_tail_slot_can_be_booked(self):
        response = self.client.post(
            f"/api/equipment/equipments/{self.equipment.id}/book/",
            {
                "date": "2026-05-21",
                "start_time": "19:00",
                "end_time": "19:30",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        booking = Booking.objects.get(id=response.data["id"])
        self.assertEqual(booking.start_time.strftime("%H:%M"), "19:00")
        self.assertEqual(booking.end_time.strftime("%H:%M"), "19:30")

    def test_xrd_already_ended_slot_cannot_be_booked(self):
        response = self.client.post(
            f"/api/equipment/equipments/{self.equipment.id}/book/",
            {
                "date": "2026-05-21",
                "start_time": "18:30",
                "end_time": "19:00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_xrd_today_last_booking_detection(self):
        first = Booking.objects.create(
            equipment=self.equipment,
            user=self.user,
            date=date(2026, 5, 21),
            start_time=time(19, 0),
            end_time=time(19, 30),
            status="active",
        )
        second = Booking.objects.create(
            equipment=self.equipment,
            user=self.next_user,
            date=date(2026, 5, 21),
            start_time=time(19, 30),
            end_time=time(20, 0),
            status="active",
        )

        self.assertFalse(first.is_today_last_xrd_booking())
        self.assertTrue(second.is_today_last_xrd_booking())

    def test_xrd_today_last_booking_ignores_cancelled_later_booking(self):
        current = Booking.objects.create(
            equipment=self.equipment,
            user=self.user,
            date=date(2026, 5, 21),
            start_time=time(19, 0),
            end_time=time(19, 30),
            status="active",
        )
        Booking.objects.create(
            equipment=self.equipment,
            user=self.next_user,
            date=date(2026, 5, 21),
            start_time=time(19, 30),
            end_time=time(20, 0),
            status="cancelled",
        )

        self.assertTrue(current.is_today_last_xrd_booking())

    def test_next_xrd_booking_can_connect_after_prior_test_ended(self):
        first = Booking.objects.create(
            equipment=self.equipment,
            user=self.user,
            date=date(2026, 5, 21),
            start_time=time(19, 0),
            end_time=time(19, 30),
            status="active",
        )
        second = Booking.objects.create(
            equipment=self.equipment,
            user=self.next_user,
            date=date(2026, 5, 21),
            start_time=time(19, 30),
            end_time=time(20, 0),
            status="active",
        )

        self.client.force_authenticate(self.next_user)
        before_response = self.client.get("/api/equipment/bookings/mine/")
        before_row = next(row for row in before_response.data if row["id"] == second.id)
        self.assertFalse(before_row["xrd_remote_connect_available"])

        self.client.force_authenticate(self.user)
        end_response = self.client.post(f"/api/equipment/bookings/{first.id}/xrd-end-test/")
        self.assertEqual(end_response.status_code, 200, end_response.data)

        first.refresh_from_db()
        self.assertIsNotNone(first.xrd_test_ended_at)
        self.assertEqual(timezone.localtime(first.xrd_test_ended_at).strftime("%H:%M"), "19:05")

        self.client.force_authenticate(self.next_user)
        after_response = self.client.get("/api/equipment/bookings/mine/")
        after_row = next(row for row in after_response.data if row["id"] == second.id)
        self.assertTrue(after_row["xrd_remote_connect_available"])


class EquipmentUsageRecordsExportTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.admin = user_model.objects.create_user(
            username="usage_export_admin",
            password="pass12345",
            name="导出管理员",
            email="usage-export-admin@example.com",
        )
        self.admin.roles.create(name="系统管理员")
        self.user = user_model.objects.create_user(
            username="usage_export_user",
            password="pass12345",
            name="=危险姓名",
            email="usage-export-user@example.com",
        )
        self.equipment = Equipment.objects.create(
            name="材料分析仪/一号",
            booking_mode=Equipment.BOOKING_MODE_STANDARD,
            time_unit_minutes=60,
            open_time_start=time(0, 0),
            open_time_end=time(23, 0),
        )
        self.other_equipment = Equipment.objects.create(
            name="另一台仪器",
            booking_mode=Equipment.BOOKING_MODE_STANDARD,
            time_unit_minutes=60,
            open_time_start=time(0, 0),
            open_time_end=time(23, 0),
        )
        self.client = APIClient()
        self.url = f"/api/equipment/equipments/{self.equipment.id}/usage-records-export/"
        set_test_now(datetime(2026, 5, 21, 12, 0))

    def tearDown(self):
        clear_test_now()

    def create_booking(self, **overrides):
        values = {
            "equipment": self.equipment,
            "user": self.user,
            "date": date(2026, 5, 21),
            "start_time": time(9, 0),
            "end_time": time(10, 0),
            "actual_duration_minutes": 60,
            "status": "active",
            "remark": "=2+2,中文备注",
        }
        values.update(overrides)
        return Booking.objects.create(**values)

    @staticmethod
    def parse_csv(response):
        content = response.content.decode("utf-8-sig")
        return list(csv.reader(StringIO(content)))

    def test_only_system_admin_can_export(self):
        self.client.force_authenticate(self.user)
        ordinary_response = self.client.get(self.url)
        self.assertEqual(ordinary_response.status_code, 403)

        self.client.force_authenticate(user=None)
        anonymous_response = self.client.get(self.url)
        self.assertEqual(anonymous_response.status_code, 401)

        self.client.force_authenticate(self.admin)
        admin_response = self.client.get(self.url)
        self.assertEqual(admin_response.status_code, 200)

    def test_csv_contains_only_completed_records_for_selected_equipment(self):
        completed = self.create_booking()
        self.create_booking(
            start_time=time(8, 0),
            end_time=time(9, 0),
            status="cancelled",
        )
        self.create_booking(
            start_time=time(11, 30),
            end_time=time(12, 30),
        )
        self.create_booking(
            start_time=time(13, 0),
            end_time=time(14, 0),
        )
        self.create_booking(
            equipment=self.other_equipment,
            start_time=time(7, 0),
            end_time=time(8, 0),
        )

        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertTrue(response.content.startswith(b"\xef\xbb\xbf"))
        self.assertIn('filename="equipment_', response["Content-Disposition"])
        self.assertIn("filename*=UTF-8''", response["Content-Disposition"])

        rows = self.parse_csv(response)
        self.assertEqual(rows[0][0:9], [
            "记录ID",
            "仪器名称",
            "仪器类型",
            "使用人",
            "学号/工号",
            "邮箱",
            "开始时间",
            "结束时间",
            "占用时长（分钟）",
        ])
        self.assertEqual(len(rows), 2)
        record = rows[1]
        self.assertEqual(record[0], str(completed.id))
        self.assertEqual(record[1], self.equipment.name)
        self.assertEqual(record[3], "'=危险姓名")
        self.assertEqual(record[6], "2026-05-21 09:00:00")
        self.assertEqual(record[7], "2026-05-21 10:00:00")
        self.assertEqual(record[8], "60")
        self.assertEqual(record[19], "'=2+2,中文备注")

    def test_legacy_completed_record_without_datetime_fields_is_exported(self):
        legacy = self.create_booking(
            date=date(2026, 5, 20),
            start_time=time(22, 0),
            end_time=time(23, 0),
            actual_duration_minutes=None,
            remark="旧记录",
        )
        Booking.objects.filter(pk=legacy.pk).update(start_at=None, end_at=None)

        self.client.force_authenticate(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        rows = self.parse_csv(response)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], str(legacy.id))
        self.assertEqual(rows[1][6], "2026-05-20 22:00:00")
        self.assertEqual(rows[1][7], "2026-05-20 23:00:00")
        self.assertEqual(rows[1][8], "60")
