from qdrant_client import QdrantClient, models


class QdrantKnowledgeStore:
    def __init__(self, config, client=None):
        self.config = config
        self.client = client or QdrantClient(
            url=config.qdrant_url, timeout=config.timeout_seconds
        )

    def ensure_collection(self):
        if self.client.collection_exists(self.config.collection):
            return
        self.client.create_collection(
            collection_name=self.config.collection,
            vectors_config=models.VectorParams(
                size=self.config.vector_size,
                distance=models.Distance.COSINE,
            ),
        )
        for field in ("domain", "visibility", "status", "document_id"):
            schema = (
                models.PayloadSchemaType.INTEGER
                if field == "document_id"
                else models.PayloadSchemaType.KEYWORD
            )
            self.client.create_payload_index(
                collection_name=self.config.collection,
                field_name=field,
                field_schema=schema,
            )

    def upsert_chunks(self, chunks, vectors):
        if len(chunks) != len(vectors):
            raise ValueError("Chunk 与向量数量不一致。")
        self.ensure_collection()
        points = []
        for chunk, vector in zip(chunks, vectors):
            if len(vector) != self.config.vector_size:
                raise ValueError(
                    f"向量维度 {len(vector)} 与配置 {self.config.vector_size} 不一致。"
                )
            document = chunk.document
            points.append(
                models.PointStruct(
                    id=str(chunk.vector_point_id),
                    vector=vector,
                    payload={
                        "chunk_id": chunk.id,
                        "document_id": document.id,
                        "domain": document.domain,
                        "visibility": document.visibility,
                        "status": "published",
                        "version": document.version,
                        "content_hash": chunk.content_hash,
                    },
                )
            )
        self.client.upsert(
            collection_name=self.config.collection,
            points=points,
            wait=True,
        )

    def search(self, vector, *, domains, visibilities, limit):
        self.ensure_collection()
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="domain", match=models.MatchAny(any=list(domains))
                ),
                models.FieldCondition(
                    key="visibility", match=models.MatchAny(any=list(visibilities))
                ),
                models.FieldCondition(
                    key="status", match=models.MatchValue(value="published")
                ),
            ]
        )
        response = self.client.query_points(
            collection_name=self.config.collection,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [
            {
                "chunk_id": int(point.payload["chunk_id"]),
                "score": float(point.score),
            }
            for point in response.points
            if point.payload and point.payload.get("chunk_id") is not None
        ]
