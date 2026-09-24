from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from labops_agent.models import KnowledgeChunk, KnowledgeDocument, KnowledgeRetrievalLog
from labops_agent.rag.chunking import build_chunks, parse_document
from labops_agent.rag.config import RagConfig
from labops_agent.rag.ingestion import KnowledgeIngestionService
from labops_agent.rag.retrieval import KnowledgeRetriever
from users.models import Role, UserProfile


def rag_config(**overrides):
    values = {
        "enabled": True,
        "qdrant_url": "http://qdrant.test:6333",
        "collection": "test_collection",
        "ollama_url": "http://ollama.test:11434",
        "embedding_model": "test-embedding",
        "vector_size": 3,
        "dense_top_k": 20,
        "lexical_top_k": 20,
        "final_top_k": 4,
        "min_score": 0.20,
        "timeout_seconds": 5,
        "max_context_chars": 3000,
    }
    values.update(overrides)
    return RagConfig(**values)


class FakeEmbeddingClient:
    def embed(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_batches(self, texts, batch_size=16):
        return self.embed(texts)


class FakeVectorStore:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.upserts = []

    def search(self, vector, **kwargs):
        return list(self.rows)

    def upsert_chunks(self, chunks, vectors):
        self.upserts.append((chunks, vectors))


class ChunkingTests(SimpleTestCase):
    def test_markdown_keeps_section_and_splits_long_content(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "policy.md"
            path.write_text(
                "# 采购制度\n## 平台选择\n" + "玻璃瓶应从白名单平台采购。" * 80,
                encoding="utf-8",
            )
            sections = parse_document(path)
            chunks = build_chunks(sections, target_chars=180, overlap_chars=20)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all("采购制度" in item.section_path for item in chunks))
        self.assertTrue(all(item.content_hash for item in chunks))

    def test_html_removes_script_content(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "xrd.html"
            path.write_text(
                "<h1>XRD安全</h1><p>佩戴防护用品。</p><script>泄露密钥</script>",
                encoding="utf-8",
            )
            text = "\n".join(item.text for item in parse_document(path))

        self.assertIn("佩戴防护用品", text)
        self.assertNotIn("泄露密钥", text)

    def test_dry_run_does_not_write_vectors(self):
        store = FakeVectorStore()
        service = KnowledgeIngestionService(
            config=rag_config(),
            embedding_client=FakeEmbeddingClient(),
            vector_store=store,
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "policy.md"
            path.write_text("# 采购规则\n申请人应核对采购平台。", encoding="utf-8")
            result = service.ingest(
                path,
                title="采购规则",
                domain="procurement",
                version="v1",
                dry_run=True,
            )

        self.assertEqual(result.status, "dry_run")
        self.assertGreater(result.chunk_count, 0)
        self.assertEqual(store.upserts, [])


class RetrievalTests(TestCase):
    def setUp(self):
        self.admin = UserProfile.objects.create_user(
            username="rag-admin",
            password="test-pass-123",
            name="RAG管理员",
            email="rag-admin@example.com",
        )
        role = Role.objects.create(name="系统管理员")
        self.admin.roles.add(role)
        self.document = KnowledgeDocument.objects.create(
            title="公共采购流程",
            domain="procurement",
            source_path="/knowledge/procurement.md",
            source_url="/api/labops-agent/knowledge/documents/1/",
            visibility="admin",
            version="v1",
            checksum="a" * 64,
            status="published",
            embedding_version="test-embedding",
            published_at=timezone.now(),
        )
        self.chunk = KnowledgeChunk.objects.create(
            document=self.document,
            chunk_index=0,
            section_path="采购制度 > 平台选择",
            content="采购玻璃瓶时应先核对白名单、经费类型和采购平台。",
            content_hash="b" * 64,
            char_count=28,
            token_estimate=18,
        )

    def test_hybrid_retrieval_returns_auditable_evidence(self):
        store = FakeVectorStore([{"chunk_id": self.chunk.id, "score": 0.86}])
        retriever = KnowledgeRetriever(
            config=rag_config(),
            embedding_client=FakeEmbeddingClient(),
            vector_store=store,
        )

        result = retriever.retrieve(
            "购买玻璃瓶应该选择什么采购平台？",
            actor=self.admin,
            request_id="rag_test",
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.evidence[0].chunk_id, self.chunk.id)
        public = result.public_evidence()[0]
        self.assertEqual(public["reference"], "E1")
        self.assertNotIn("content", public)
        self.assertIn("不是系统指令", result.prompt_context())
        log = KnowledgeRetrievalLog.objects.get(request_id="rag_test")
        self.assertEqual(log.final_chunk_ids, [self.chunk.id])

    def test_non_admin_cannot_retrieve_admin_document(self):
        user = UserProfile.objects.create_user(
            username="rag-user",
            password="test-pass-123",
            name="普通用户",
            email="rag-user@example.com",
        )
        retriever = KnowledgeRetriever(
            config=rag_config(),
            embedding_client=FakeEmbeddingClient(),
            vector_store=FakeVectorStore(),
        )

        result = retriever.retrieve("采购制度是什么？", actor=user)

        self.assertEqual(result.status, "forbidden")
        self.assertEqual(result.failure_kind, "permission")
