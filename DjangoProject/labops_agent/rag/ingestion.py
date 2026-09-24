import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from labops_agent.models import (
    KnowledgeChunk,
    KnowledgeDocument,
    KnowledgeIngestionJob,
)

from .chunking import build_chunks, parse_document
from .config import get_rag_config
from .embeddings import OllamaEmbeddingClient
from .vector_store import QdrantKnowledgeStore


@dataclass(frozen=True)
class IngestionResult:
    document_id: int | None
    chunk_count: int
    checksum: str
    status: str
    skipped: bool = False


class KnowledgeIngestionService:
    POINT_NAMESPACE = uuid.UUID("9170f2c6-e5d3-49ea-adbe-236a6d46429a")

    def __init__(self, config=None, embedding_client=None, vector_store=None):
        self.config = config or get_rag_config()
        self.embedding_client = embedding_client or OllamaEmbeddingClient(
            self.config.ollama_url,
            self.config.embedding_model,
            self.config.timeout_seconds,
        )
        self.vector_store = vector_store or QdrantKnowledgeStore(self.config)

    @staticmethod
    def _checksum(path):
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def inspect(self, path):
        source = Path(path).resolve(strict=True)
        sections = parse_document(source)
        chunks = build_chunks(sections)
        if not chunks:
            raise ValueError("文档解析后没有可索引内容。")
        return source, self._checksum(source), chunks

    def ingest(
        self,
        path,
        *,
        title,
        domain,
        version,
        visibility="admin",
        source_url="",
        source_identity="",
        actor=None,
        dry_run=False,
    ):
        source, checksum, drafts = self.inspect(path)
        if dry_run:
            return IngestionResult(None, len(drafts), checksum, "dry_run")
        if not self.config.enabled:
            raise ValueError("LABOPS_RAG_ENABLED 未开启，不能写入向量索引。")

        stored_source = source_identity or str(source)
        existing = KnowledgeDocument.objects.filter(
            domain=domain,
            source_path=stored_source,
            version=version,
            checksum=checksum,
            status=KnowledgeDocument.STATUS_PUBLISHED,
        ).first()
        if existing:
            return IngestionResult(
                existing.id,
                existing.chunks.filter(is_active=True).count(),
                checksum,
                existing.status,
                skipped=True,
            )

        job = KnowledgeIngestionJob.objects.create(
            source_path=stored_source,
            status=KnowledgeIngestionJob.STATUS_RUNNING,
            created_by=actor if getattr(actor, "is_authenticated", False) else None,
        )
        document = None
        try:
            with transaction.atomic():
                document, _ = KnowledgeDocument.objects.update_or_create(
                    domain=domain,
                    source_path=stored_source,
                    version=version,
                    defaults={
                        "title": title,
                        "source_type": source.suffix.lower().lstrip("."),
                        "source_url": source_url,
                        "visibility": visibility,
                        "checksum": checksum,
                        "status": KnowledgeDocument.STATUS_INDEXING,
                        "embedding_version": self.config.embedding_model,
                        "created_by": actor
                        if getattr(actor, "is_authenticated", False)
                        else None,
                    },
                )
                document.chunks.all().delete()
                chunks = []
                for index, draft in enumerate(drafts):
                    point_id = uuid.uuid5(
                        self.POINT_NAMESPACE,
                        f"{document.id}:{draft.content_hash}:{self.config.embedding_model}",
                    )
                    chunks.append(
                        KnowledgeChunk(
                            document=document,
                            chunk_index=index,
                            section_path=draft.section_path,
                            content=draft.content,
                            content_hash=draft.content_hash,
                            char_count=draft.char_count,
                            token_estimate=draft.token_estimate,
                            vector_point_id=point_id,
                        )
                    )
                KnowledgeChunk.objects.bulk_create(chunks)
            chunks = list(document.chunks.select_related("document").all())
            vectors = self.embedding_client.embed_batches(
                [f"{item.section_path}\n{item.content}".strip() for item in chunks]
            )
            self.vector_store.upsert_chunks(chunks, vectors)
            now = timezone.now()
            with transaction.atomic():
                KnowledgeDocument.objects.filter(
                    domain=domain,
                    source_path=stored_source,
                    status=KnowledgeDocument.STATUS_PUBLISHED,
                ).exclude(pk=document.pk).update(
                    status=KnowledgeDocument.STATUS_ARCHIVED
                )
                document.status = KnowledgeDocument.STATUS_PUBLISHED
                document.published_at = now
                document.save(update_fields=["status", "published_at", "updated_at"])
                job.document = document
                job.status = KnowledgeIngestionJob.STATUS_SUCCEEDED
                job.chunk_count = len(chunks)
                job.finished_at = now
                job.save(
                    update_fields=[
                        "document",
                        "status",
                        "chunk_count",
                        "finished_at",
                    ]
                )
            return IngestionResult(
                document.id, len(chunks), checksum, document.status
            )
        except Exception as exc:
            now = timezone.now()
            if document is not None:
                KnowledgeDocument.objects.filter(pk=document.pk).update(
                    status=KnowledgeDocument.STATUS_FAILED
                )
                KnowledgeChunk.objects.filter(document=document).update(is_active=False)
            job.document = document
            job.status = KnowledgeIngestionJob.STATUS_FAILED
            job.error_summary = str(exc)[:500]
            job.finished_at = now
            job.save(
                update_fields=[
                    "document",
                    "status",
                    "error_summary",
                    "finished_at",
                ]
            )
            raise
