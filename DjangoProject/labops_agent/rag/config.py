from dataclasses import dataclass

from django.conf import settings

from labops_agent.exceptions import AgentConfigurationError


def _integer(value, name, minimum, maximum):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise AgentConfigurationError(f"{name} 必须是整数。") from exc
    if not minimum <= parsed <= maximum:
        raise AgentConfigurationError(f"{name} 必须在 {minimum}-{maximum} 之间。")
    return parsed


def _number(value, name, minimum, maximum):
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise AgentConfigurationError(f"{name} 必须是数字。") from exc
    if not minimum <= parsed <= maximum:
        raise AgentConfigurationError(f"{name} 必须在 {minimum}-{maximum} 之间。")
    return parsed


@dataclass(frozen=True)
class RagConfig:
    enabled: bool
    qdrant_url: str
    collection: str
    ollama_url: str
    embedding_model: str
    vector_size: int
    dense_top_k: int
    lexical_top_k: int
    final_top_k: int
    min_score: float
    timeout_seconds: int
    max_context_chars: int


def get_rag_config():
    raw = getattr(settings, "LABOPS_RAG", {})
    return RagConfig(
        enabled=bool(raw.get("ENABLED", False)),
        qdrant_url=str(raw.get("QDRANT_URL", "")).rstrip("/"),
        collection=str(raw.get("QDRANT_COLLECTION", "labops_knowledge_v1")),
        ollama_url=str(raw.get("OLLAMA_URL", "")).rstrip("/"),
        embedding_model=str(raw.get("EMBEDDING_MODEL", "bge-m3")),
        vector_size=_integer(raw.get("VECTOR_SIZE", 1024), "VECTOR_SIZE", 64, 4096),
        dense_top_k=_integer(raw.get("DENSE_TOP_K", 20), "DENSE_TOP_K", 1, 100),
        lexical_top_k=_integer(raw.get("LEXICAL_TOP_K", 20), "LEXICAL_TOP_K", 1, 100),
        final_top_k=_integer(raw.get("FINAL_TOP_K", 4), "FINAL_TOP_K", 1, 10),
        min_score=_number(raw.get("MIN_SCORE", 0.20), "MIN_SCORE", -1.0, 1.0),
        timeout_seconds=_integer(raw.get("TIMEOUT_SECONDS", 10), "TIMEOUT_SECONDS", 1, 120),
        max_context_chars=_integer(
            raw.get("MAX_CONTEXT_CHARS", 3000), "MAX_CONTEXT_CHARS", 500, 10000
        ),
    )
