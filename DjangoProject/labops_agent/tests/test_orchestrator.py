from django.test import SimpleTestCase

from labops_agent.config import AgentConfig
from labops_agent.exceptions import ToolProtocolError
from labops_agent.orchestrator import AgentOrchestrator
from labops_agent.tools.registry import ToolExecutionResult


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


class FakeRegistry:
    def __init__(self, data=None):
        self.calls = []
        self.data = data or {"count": 0, "reservations": []}

    def execute(self, name, arguments, actor):
        self.calls.append((name, arguments, actor))
        return ToolExecutionResult(
            name=name,
            domain="equipment",
            ok=True,
            data=self.data,
        )


class FakeContextService:
    def __init__(self, context=None):
        self.context = context or {}

    def prefetch(self, question):
        return self.context


class FakeEquipmentContextService:
    def __init__(self, context=None):
        self.context = context or {}

    def prefetch(self, question, actor):
        return self.context


def message_response(text):
    return {
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ]
    }


class AgentOrchestratorTests(SimpleTestCase):
    def setUp(self):
        self.actor = object()
        self.config = AgentConfig(
            enabled=True,
            base_url="https://provider.example/v1",
            api_key="secret",
            model="test-model",
            timeout_seconds=10,
            max_tool_rounds=2,
        )

    def test_executes_tool_with_actor_then_returns_answer(self):
        client = FakeClient(
            [
                {
                    "output": [
                        {
                            "type": "function_call",
                            "name": "get_my_reservations",
                            "arguments": (
                                '{"upcoming":true,"start_date":null,'
                                '"end_date":null,"statuses":null,"limit":10}'
                            ),
                            "call_id": "call_1",
                        }
                    ]
                },
                message_response("你目前没有未来预约。"),
            ]
        )
        registry = FakeRegistry()
        orchestrator = AgentOrchestrator(
            self.config,
            client=client,
            registry=registry,
            tools=[{"type": "function", "name": "get_my_reservations"}],
        )

        result = orchestrator.run(self.actor, "我接下来有哪些仪器预约？")

        self.assertEqual(result.answer, "你目前没有未来预约。")
        self.assertEqual(result.domain, "equipment")
        self.assertEqual(result.tools, [{"name": "get_my_reservations", "status": "success"}])
        self.assertIs(registry.calls[0][2], self.actor)
        second_input = client.calls[1]["input_items"]
        self.assertEqual(second_input[-2]["type"], "function_call")
        self.assertEqual(second_input[-1]["type"], "function_call_output")
        self.assertNotIn("user_id", second_input[-1]["output"])
        self.assertFalse(any(call.get("store") for call in client.calls))
        self.assertTrue(result.conversation_id)

    def test_langgraph_has_explicit_controlled_nodes(self):
        orchestrator = AgentOrchestrator(
            self.config,
            client=FakeClient([message_response("好的。")]),
            registry=FakeRegistry(),
            tools=[],
        )

        node_names = orchestrator._get_graph().node_names

        self.assertTrue(
            {"prepare_context", "call_model", "execute_tools", "finalize"}
            <= node_names
        )

    def test_includes_history_prefetched_context_and_action(self):
        action = {"id": "draft-1", "type": "procurement_create"}
        client = FakeClient(
            [
                {
                    "output": [
                        {
                            "type": "function_call",
                            "name": "prepare_procurement_request",
                            "arguments": "{}",
                            "call_id": "call_prepare",
                        }
                    ]
                },
                message_response("草稿已生成，请点击确认。"),
            ]
        )
        orchestrator = AgentOrchestrator(
            self.config,
            client=client,
            registry=FakeRegistry({"status": "ready", "action": action}),
            tools=[],
            context_service=FakeContextService({"whitelist_candidates": [{"id": 1}]}),
        )

        result = orchestrator.run(
            self.actor,
            "每瓶80元",
            history=[{"role": "user", "content": "我要采购乙醇"}],
        )

        self.assertEqual(result.actions, [action])
        first_call = client.calls[0]
        self.assertEqual(first_call["input_items"][0]["content"], "我要采购乙醇")
        self.assertIn("whitelist_candidates", first_call["instructions"])

    def test_includes_deterministic_equipment_alias_context(self):
        client = FakeClient([message_response("已识别为输力强通道3。")])
        orchestrator = AgentOrchestrator(
            self.config,
            client=client,
            registry=FakeRegistry(),
            tools=[],
            equipment_context_service=FakeEquipmentContextService(
                {
                    "equipment_candidates": [
                        {"id": 7, "name": "输力强电化学工作站"}
                    ],
                    "extracted_position_no": 3,
                }
            ),
        )

        orchestrator.run(self.actor, "帮我预约三号输力强")

        instructions = client.calls[0]["instructions"]
        self.assertIn("输力强电化学工作站", instructions)
        self.assertIn('"extracted_position_no":3', instructions)

    def test_invalid_tool_json_stops_before_business_execution(self):
        client = FakeClient(
            [
                {
                    "output": [
                        {
                            "type": "function_call",
                            "name": "search_equipment",
                            "arguments": "not-json",
                            "call_id": "call_bad",
                        }
                    ]
                }
            ]
        )
        registry = FakeRegistry()
        orchestrator = AgentOrchestrator(
            self.config, client=client, registry=registry, tools=[]
        )

        with self.assertRaises(ToolProtocolError):
            orchestrator.run(self.actor, "查仪器")
        self.assertEqual(registry.calls, [])

    def test_provider_cannot_exceed_tool_round_limit(self):
        config = AgentConfig(**{**self.config.__dict__, "max_tool_rounds": 1})
        repeated_call = {
            "output": [
                {
                    "type": "function_call",
                    "name": "get_my_reservations",
                    "arguments": "{}",
                    "call_id": "call_repeat",
                }
            ]
        }
        client = FakeClient([repeated_call, repeated_call])
        orchestrator = AgentOrchestrator(
            config, client=client, registry=FakeRegistry(), tools=[]
        )

        with self.assertRaisesMessage(ToolProtocolError, "轮次"):
            orchestrator.run(self.actor, "反复查询")
        self.assertEqual(client.calls[-1]["tool_choice"], "none")

    def test_can_fall_back_to_legacy_loop(self):
        config = AgentConfig(**{**self.config.__dict__, "use_langgraph": False})
        client = FakeClient([message_response("旧编排仍可回退。")])
        orchestrator = AgentOrchestrator(config, client=client, tools=[])

        result = orchestrator.run(self.actor, "测试回退")

        self.assertEqual(result.answer, "旧编排仍可回退。")
        self.assertIsNone(orchestrator._graph)
