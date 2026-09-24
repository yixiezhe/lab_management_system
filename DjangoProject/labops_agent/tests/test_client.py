from types import SimpleNamespace

from django.test import SimpleTestCase

from labops_agent.config import AgentConfig
from labops_agent.exceptions import LLMProviderError
from labops_agent.llm.client import ResponsesClient


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {"output": []}

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class ResponsesClientTests(SimpleTestCase):
    def setUp(self):
        self.config = AgentConfig(
            enabled=True,
            base_url="https://provider.example/v1",
            api_key="test-secret",
            model="test-model",
            timeout_seconds=10,
            max_tool_rounds=2,
        )

    def test_request_is_stateless_and_server_side_authenticated(self):
        session = FakeSession(FakeResponse(payload={"output": []}))
        client = ResponsesClient(self.config, session=session)

        client.create(
            input_items=[{"role": "user", "content": "test"}],
            tools=[],
            tool_choice="none",
            instructions="test instructions",
        )

        url, kwargs = session.calls[0]
        self.assertEqual(url, "https://provider.example/v1/responses")
        self.assertFalse(kwargs["json"]["store"])
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-secret")
        self.assertEqual(kwargs["timeout"], 10)

    def test_http_error_is_replaced_with_safe_provider_error(self):
        session = FakeSession(FakeResponse(status_code=401, payload={"secret": "body"}))
        client = ResponsesClient(self.config, session=session)

        with self.assertRaisesMessage(LLMProviderError, "401"):
            client.create(
                input_items=[],
                tools=[],
                tool_choice="none",
                instructions="test",
            )
