from dataclasses import dataclass

import requests


class EmbeddingServiceError(RuntimeError):
    pass


@dataclass
class OllamaEmbeddingClient:
    base_url: str
    model: str
    timeout_seconds: int = 10
    session: object = None

    def __post_init__(self):
        if self.session is None:
            self.session = requests.Session()

    def embed(self, texts):
        values = [str(text or "").strip() for text in texts]
        if not values or any(not value for value in values):
            raise EmbeddingServiceError("Embedding 输入不能为空。")
        try:
            response = self.session.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": values},
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            raise EmbeddingServiceError("本地 Embedding 服务不可用。") from exc
        if response.status_code >= 400:
            raise EmbeddingServiceError(
                f"本地 Embedding 服务返回异常状态（{response.status_code}）。"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise EmbeddingServiceError("Embedding 服务返回了无效 JSON。") from exc
        embeddings = data.get("embeddings") if isinstance(data, dict) else None
        if not isinstance(embeddings, list) or len(embeddings) != len(values):
            raise EmbeddingServiceError("Embedding 返回数量与输入不一致。")
        if any(not isinstance(vector, list) or not vector for vector in embeddings):
            raise EmbeddingServiceError("Embedding 返回了无效向量。")
        return embeddings

    def embed_batches(self, texts, batch_size=16):
        vectors = []
        for index in range(0, len(texts), batch_size):
            vectors.extend(self.embed(texts[index : index + batch_size]))
        return vectors
