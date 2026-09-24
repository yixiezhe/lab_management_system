from datetime import time, timedelta

from django.test import TestCase

from equipment.models import Booking, Equipment
from equipment.time_control import get_controlled_today
from labops_agent.services import (
    EquipmentContextService,
    EquipmentReservationActionService,
)
from users.models import Role, UserProfile


class EquipmentReservationActionTests(TestCase):
    def setUp(self):
        self.admin = UserProfile.objects.create_user(
            username="equipment-agent-admin",
            password="test-pass-123",
            name="仪器助手管理员",
            email="equipment-agent@example.com",
        )
        admin_role, _ = Role.objects.get_or_create(name="系统管理员")
        self.admin.roles.add(admin_role)
        self.equipment = Equipment.objects.create(
            name="输力强电化学工作站",
            booking_mode=Equipment.BOOKING_MODE_ELECTROCHEMICAL_WORKSTATION,
            time_unit_minutes=30,
        )
        self.target_date = get_controlled_today() + timedelta(days=1)

    def build_args(self):
        return {
            "equipment_id": None,
            "equipment_query": "三号输力强",
            "target_date": self.target_date,
            "start_time": time(8, 0),
            "end_time": None,
            "duration_minutes": 120,
            "position_no": None,
        }

    def test_context_resolves_alias_and_channel(self):
        context = EquipmentContextService().prefetch("明早8点预约三号输力强2小时", self.admin)

        self.assertEqual(context["extracted_position_no"], 3)
        self.assertEqual(context["equipment_candidates"][0]["id"], self.equipment.id)

    def test_prepares_prefill_without_creating_booking(self):
        result = EquipmentReservationActionService.prepare(self.admin, self.build_args())

        self.assertEqual(result["status"], "ready")
        preview = result["action"]["preview"]
        self.assertEqual(preview["equipment_name"], "输力强电化学工作站")
        self.assertEqual(preview["position_no"], 3)
        self.assertEqual(preview["start_time"], "08:00")
        self.assertEqual(preview["end_time"], "10:00")
        self.assertEqual(preview["duration_minutes"], 120)
        self.assertFalse(Booking.objects.exists())

    def test_conflict_returns_no_action(self):
        Booking.objects.create(
            equipment=self.equipment,
            user=self.admin,
            date=self.target_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            position_no=3,
            status="active",
        )

        result = EquipmentReservationActionService.prepare(self.admin, self.build_args())

        self.assertEqual(result["status"], "unavailable")
        self.assertNotIn("action", result)
        self.assertEqual(result["blocked_slots"][0]["start"], "09:00")
