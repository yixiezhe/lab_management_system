from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from labops_agent.orchestrator import AgentResult
from users.models import Role, UserProfile


ENABLED_SETTINGS = {
    "ENABLED": True,
    "BASE_URL": "https://provider.example/v1",
    "API_KEY": "test-secret",
    "MODEL": "test-model",
    "TIMEOUT_SECONDS": "10",
    "MAX_TOOL_ROUNDS": "2",
}


class AgentQueryApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = UserProfile.objects.create_user(
            username="api-user",
            password="test-pass-123",
            name="API用户",
            email="api-user@example.com",
        )
        self.admin = UserProfile.objects.create_user(
            username="agent-admin",
            password="test-pass-123",
            name="Agent管理员",
            email="agent-admin@example.com",
        )
        admin_role = Role.objects.create(name="系统管理员")
        self.admin.roles.add(admin_role)
        self.url = reverse("labops-agent-query")

    def test_requires_authentication(self):
        response = self.client.post(self.url, {"question": "我的预约？"}, format="json")
        self.assertEqual(response.status_code, 401)

    @override_settings(LABOPS_AGENT=ENABLED_SETTINGS)
    def test_rejects_authenticated_non_admin_before_provider_call(self):
        self.client.force_authenticate(self.user)
        with patch("labops_agent.views.AgentOrchestrator") as orchestrator:
            response = self.client.post(
                self.url, {"question": "我的预约？"}, format="json"
            )

        self.assertEqual(response.status_code, 403)
        orchestrator.assert_not_called()

    @override_settings(
        LABOPS_AGENT={
            **ENABLED_SETTINGS,
            "ENABLED": False,
            "API_KEY": "",
        }
    )
    def test_disabled_feature_does_not_call_provider(self):
        self.client.force_authenticate(self.admin)
        with patch("labops_agent.views.AgentOrchestrator") as orchestrator:
            response = self.client.post(
                self.url, {"question": "我的预约？"}, format="json"
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "agent_disabled")
        orchestrator.assert_not_called()

    @override_settings(LABOPS_AGENT=ENABLED_SETTINGS)
    @patch("labops_agent.views.AgentOrchestrator")
    def test_returns_auditable_tool_summary(self, orchestrator_class):
        orchestrator_class.return_value.run.return_value = AgentResult(
            answer="你目前没有预约。",
            domain="equipment",
            tools=[{"name": "get_my_reservations", "status": "success"}],
            request_id="agt_test",
            actions=[],
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.url, {"question": "我的预约？"}, format="json"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["domain"], "equipment")
        self.assertEqual(response.data["request_id"], "agt_test")
        self.assertEqual(response.data["conversation_id"], "")
        self.assertEqual(response.data["actions"], [])
        self.assertNotIn("reasoning", response.data)
        args = orchestrator_class.return_value.run.call_args.args
        self.assertEqual(args, (self.admin, "我的预约？"))
        self.assertEqual(
            orchestrator_class.return_value.run.call_args.kwargs,
            {"history": [], "conversation_id": None},
        )

    @override_settings(LABOPS_AGENT=ENABLED_SETTINGS)
    def test_question_length_is_bounded_before_provider_call(self):
        self.client.force_authenticate(self.admin)
        response = self.client.post(
            self.url, {"question": "问" * 1001}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    @override_settings(LABOPS_AGENT=ENABLED_SETTINGS)
    @patch("labops_agent.views.AgentOrchestrator")
    def test_passes_bounded_history_to_orchestrator(self, orchestrator_class):
        orchestrator_class.return_value.run.return_value = AgentResult(
            answer="请补充单价。",
            domain="procurement",
            tools=[],
            request_id="agt_history",
            actions=[],
        )
        self.client.force_authenticate(self.admin)
        history = [{"role": "user", "content": "我要买乙醇"}]

        response = self.client.post(
            self.url,
            {"question": "每瓶80元", "history": history},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            orchestrator_class.return_value.run.call_args.kwargs,
            {"history": history, "conversation_id": None},
        )

    @override_settings(LABOPS_AGENT=ENABLED_SETTINGS)
    @patch("labops_agent.views.AgentOrchestrator")
    def test_passes_conversation_id_to_orchestrator(self, orchestrator_class):
        conversation_id = "d16f94d2-b0a7-426d-b10c-fb8e91a53709"
        orchestrator_class.return_value.run.return_value = AgentResult(
            answer="已读取会话。",
            domain="general",
            tools=[],
            request_id="agt_conversation",
            actions=[],
            conversation_id=conversation_id,
        )
        self.client.force_authenticate(self.admin)

        response = self.client.post(
            self.url,
            {"question": "改成四号", "conversation_id": conversation_id},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["conversation_id"], conversation_id)
        self.assertEqual(
            orchestrator_class.return_value.run.call_args.kwargs["conversation_id"].hex,
            conversation_id.replace("-", ""),
        )
