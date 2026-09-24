from dataclasses import dataclass

import requests

from labops_agent.exceptions import LLMProviderError


@dataclass
class ResponsesClient:
    config: object
    session: object = None

    def __post_init__(self):
        if self.session is None:
            self.session = requests.Session()

    def create(self, *, input_items, tools, tool_choice, instructions):
        payload = {
            "model": self.config.model,
            "instructions": instructions,
            "input": input_items,
            "tools": tools,
            "tool_choice": tool_choice,
            "store": False,
            "max_output_tokens": 600,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        try:
            response = self.session.post(
                f"{self.config.base_url}/responses",
                headers=headers,
                json=payload,
                timeout=self.config.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise LLMProviderError("模型服务暂时无法连接。") from exc

        if response.status_code >= 400:
            raise LLMProviderError(
                f"模型服务返回异常状态（{response.status_code}）。"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise LLMProviderError("模型服务返回了无效的 JSON。") from exc
        if not isinstance(data, dict):
            raise LLMProviderError("模型服务响应格式无效。")
        if data.get("error"):
            raise LLMProviderError("模型服务返回了错误。")
        return data
