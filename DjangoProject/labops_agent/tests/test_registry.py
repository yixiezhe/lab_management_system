from datetime import date, time

from django.test import TestCase

from equipment.models import Booking, Equipment
from labops_agent.tools.registry import ToolRegistry
from users.models import UserProfile


class ToolRegistryTests(TestCase):
    def setUp(self):
        self.registry = ToolRegistry()
        self.user = self.create_user("agent-user", "Agent用户")
        self.other = self.create_user("other-user", "其他用户")
        self.equipment = Equipment.objects.create(name="Agent测试仪器")

    @staticmethod
    def create_user(username, name):
        return UserProfile.objects.create_user(
            username=username,
            password="test-pass-123",
            name=name,
            email=f"{username}@example.com",
        )

    def create_booking(self, user, start, end):
        return Booking.objects.create(
            equipment=self.equipment,
            user=user,
            date=date(2099, 1, 1),
            start_time=start,
            end_time=end,
            status="active",
        )

    def test_model_cannot_submit_user_id(self):
        result = self.registry.execute(
            "get_my_reservations",
            {"upcoming": None, "limit": 10, "user_id": self.other.id},
            self.user,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_my_reservations_uses_authenticated_actor_only(self):
        mine = self.create_booking(self.user, time(9, 0), time(10, 0))
        self.create_booking(self.other, time(10, 0), time(11, 0))

        result = self.registry.execute(
            "get_my_reservations",
            {"upcoming": None, "limit": 10},
            self.user,
        )

        self.assertTrue(result.ok)
        self.assertEqual([row["id"] for row in result.data], [mine.id])

    def test_unknown_tool_is_not_executed(self):
        result = self.registry.execute("delete_booking", {}, self.user)

        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "unknown_tool")
