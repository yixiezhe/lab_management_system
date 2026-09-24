class AgentError(Exception):
    """Base exception for safe Agent API failures."""


class AgentDisabledError(AgentError):
    pass


class AgentConfigurationError(AgentError):
    pass


class LLMProviderError(AgentError):
    pass


class ToolProtocolError(AgentError):
    pass
