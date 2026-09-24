import uuid

from django.test import TestCase

from labops_agent.models import AgentConversation
from labops_agent.services.conversation_state import ConversationStateService
from labops_agent.tools.registry import ToolExecutionResult
from users.models import UserProfile


class ConversationStateServiceTests(TestCase):
    def setUp(self):
        self.user = UserProfile.objects.create_user(
            username="conversation-user",
            password="test-pass-123",
            name="会话用户",
            email="conversation@example.com",
        )
        self.other_user = UserProfile.objects.create_user(
            username="other-conversation-user",
            password="test-pass-123",
            name="其他会话用户",
            email="other-conversation@example.com",
        )
        self.service = ConversationStateService()

    def test_reuses_only_the_actors_own_conversation(self):
        first = self.service.load_or_create(self.user)
        reused = self.service.load_or_create(self.user, first.id)
        isolated = self.service.load_or_create(self.other_user, first.id)

        self.assertEqual(reused.id, first.id)
        self.assertNotEqual(isolated.id, first.id)

    def test_remembers_compact_validated_equipment_preview(self):
        session = self.service.load_or_create(self.user)
        preview = {
            "equipment_id": 8,
            "equipment_name": "输力强电化学工作站",
            "target_date": "2026-09-03",
            "start_time": "08:00",
            "end_time": "10:00",
            "position_no": 3,
        }
        result = ToolExecutionResult(
            name="prepare_equipment_reservation",
            domain="equipment",
            ok=True,
            data={
                "status": "ready",
                "action": {
                    "type": "equipment_reservation_prefill",
                    "preview": preview,
                },
            },
        )

        self.service.remember_tool_result(
            session,
            "prepare_equipment_reservation",
            {"equipment_query": "三号输力强"},
            result,
        )

        saved = AgentConversation.objects.get(pk=session.id)
        self.assertEqual(saved.state["equipment_draft"], preview)
        self.assertEqual(saved.state["last_domain"], "equipment")

    def test_unknown_conversation_id_starts_a_new_session(self):
        session = self.service.load_or_create(self.user, uuid.uuid4())

        self.assertTrue(AgentConversation.objects.filter(pk=session.id).exists())
