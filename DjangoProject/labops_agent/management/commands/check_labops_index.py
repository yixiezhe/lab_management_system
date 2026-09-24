from django.core.management.base import BaseCommand, CommandError

from labops_agent.models import KnowledgeChunk, KnowledgeDocument
from labops_agent.rag.config import get_rag_config
from labops_agent.rag.embeddings import OllamaEmbeddingClient
from labops_agent.rag.vector_store import QdrantKnowledgeStore


class Command(BaseCommand):
    help = "检查 LabOps MySQL 知识元数据、Qdrant 点数和可选 Embedding 探针"

    def add_arguments(self, parser):
        parser.add_argument("--probe-embedding", action="store_true")

    def handle(self, *args, **options):
        config = get_rag_config()
        documents = KnowledgeDocument.objects.filter(status="published").count()
        chunks = KnowledgeChunk.objects.filter(
            is_active=True, document__status="published"
        ).count()
        try:
            store = QdrantKnowledgeStore(config)
            store.ensure_collection()
            collection = store.client.get_collection(config.collection)
            points = int(collection.points_count or 0)
        except Exception as exc:
            raise CommandError(f"Qdrant 检查失败：{exc}") from exc
        if points < chunks:
            raise CommandError(
                f"索引不完整：MySQL active chunks={chunks}, Qdrant points={points}"
            )

        dimensions = "未探测"
        if options["probe_embedding"]:
            try:
                vector = OllamaEmbeddingClient(
                    config.ollama_url,
                    config.embedding_model,
                    config.timeout_seconds,
                ).embed(["实验室知识索引健康检查"])[0]
            except Exception as exc:
                raise CommandError(f"Embedding 检查失败：{exc}") from exc
            dimensions = len(vector)
            if dimensions != config.vector_size:
                raise CommandError(
                    f"Embedding 维度异常：actual={dimensions}, expected={config.vector_size}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"索引健康：documents={documents}, chunks={chunks}, "
                f"qdrant_points={points}, embedding_dimensions={dimensions}"
            )
        )
