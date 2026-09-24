from dataclasses import dataclass

from django.conf import settings

from .exceptions import AgentConfigurationError, AgentDisabledError


def _bounded_int(value, *, name, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise AgentConfigurationError(f"{name} 配置必须是整数。") from exc
    if not minimum <= parsed <= maximum:
        raise AgentConfigurationError(
            f"{name} 配置必须在 {minimum}-{maximum} 之间。"
        )
    return parsed


def _as_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


@dataclass(frozen=True)
class AgentConfig:
    enabled: bool
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int
    max_tool_rounds: int
    use_langgraph: bool = True

    def validate_for_request(self):
        if not self.enabled:
            raise AgentDisabledError("智能查询功能尚未启用。")
        if not self.base_url.startswith(("https://", "http://")):
            raise AgentConfigurationError("模型服务地址配置无效。")
        if not self.api_key:
            raise AgentConfigurationError("模型服务令牌尚未配置。")
        if not self.model:
            raise AgentConfigurationError("模型名称尚未配置。")


def get_agent_config():
    raw = getattr(settings, "LABOPS_AGENT", {})
    return AgentConfig(
        enabled=_as_bool(raw.get("ENABLED"), False),
        base_url=str(raw.get("BASE_URL", "")).rstrip("/"),
        api_key=str(raw.get("API_KEY", "")),
        model=str(raw.get("MODEL", "gpt-5.6-luna")),
        timeout_seconds=_bounded_int(
            raw.get("TIMEOUT_SECONDS", 30),
            name="LABOPS_LLM_TIMEOUT",
            minimum=3,
            maximum=120,
        ),
        max_tool_rounds=_bounded_int(
            raw.get("MAX_TOOL_ROUNDS", 2),
            name="LABOPS_LLM_MAX_TOOL_ROUNDS",
            minimum=1,
            maximum=4,
        ),
        use_langgraph=_as_bool(raw.get("USE_LANGGRAPH"), True),
    )
