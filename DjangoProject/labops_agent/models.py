import uuid

from django.conf import settings
from django.db import models


class AgentActionDraft(models.Model):
    ACTION_PROCUREMENT_CREATE = "procurement_create"
    ACTION_CHOICES = [(ACTION_PROCUREMENT_CREATE, "创建采购申请")]

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待确认"),
        (STATUS_CONFIRMED, "已确认"),
        (STATUS_EXPIRED, "已过期"),
        (STATUS_CANCELLED, "已取消"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_action_drafts",
    )
    action_type = models.CharField(max_length=40, choices=ACTION_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    payload = models.JSONField(default=dict)
    resolution = models.JSONField(default=dict)
    expires_at = models.DateTimeField(db_index=True)
    target_object_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["actor", "status", "action_type"],
                name="labops_actor_status_type_idx",
            )
        ]


class AgentConversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="agent_conversations",
    )
    state = models.JSONField(default=dict)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["actor", "updated_at"],
                name="labops_conv_actor_updated_idx",
            )
        ]


class KnowledgeDocument(models.Model):
    DOMAIN_PROCUREMENT = "procurement"
    DOMAIN_EQUIPMENT = "equipment"
    DOMAIN_CHOICES = [
        (DOMAIN_PROCUREMENT, "采购"),
        (DOMAIN_EQUIPMENT, "仪器"),
    ]

    VISIBILITY_ADMIN = "admin"
    VISIBILITY_PUBLIC = "public"
    VISIBILITY_CHOICES = [
        (VISIBILITY_ADMIN, "仅管理员"),
        (VISIBILITY_PUBLIC, "公开"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_INDEXING = "indexing"
    STATUS_PUBLISHED = "published"
    STATUS_FAILED = "failed"
    STATUS_ARCHIVED = "archived"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_INDEXING, "索引中"),
        (STATUS_PUBLISHED, "已发布"),
        (STATUS_FAILED, "失败"),
        (STATUS_ARCHIVED, "已归档"),
    ]

    title = models.CharField(max_length=200)
    domain = models.CharField(max_length=30, choices=DOMAIN_CHOICES, db_index=True)
    source_type = models.CharField(max_length=30, default="markdown")
    source_path = models.CharField(max_length=500)
    source_url = models.CharField(max_length=500, blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=VISIBILITY_CHOICES, default=VISIBILITY_ADMIN, db_index=True
    )
    version = models.CharField(max_length=80)
    checksum = models.CharField(max_length=64, db_index=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    effective_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    parser_version = models.CharField(max_length=80, default="labops-parser-v1")
    embedding_version = models.CharField(max_length=120, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_knowledge_documents",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["domain", "source_path", "version"],
                name="labops_knowledge_source_version_uniq",
            )
        ]


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(
        KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks"
    )
    chunk_index = models.PositiveIntegerField()
    section_path = models.CharField(max_length=500, blank=True, default="")
    content = models.TextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    char_count = models.PositiveIntegerField(default=0)
    token_estimate = models.PositiveIntegerField(default=0)
    vector_point_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["document_id", "chunk_index"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="labops_knowledge_document_chunk_uniq",
            )
        ]


class KnowledgeIngestionJob(models.Model):
    STATUS_RUNNING = "running"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_DRY_RUN = "dry_run"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCEEDED, "成功"),
        (STATUS_FAILED, "失败"),
        (STATUS_DRY_RUN, "仅检查"),
    ]

    document = models.ForeignKey(
        KnowledgeDocument,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ingestion_jobs",
    )
    source_path = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    chunk_count = models.PositiveIntegerField(default=0)
    error_summary = models.CharField(max_length=500, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_ingestion_jobs",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)


class KnowledgeRetrievalLog(models.Model):
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="knowledge_retrieval_logs",
    )
    request_id = models.CharField(max_length=64, db_index=True)
    domain = models.CharField(max_length=30, blank=True, default="")
    route = models.CharField(max_length=40, default="rag")
    status = models.CharField(max_length=30, db_index=True)
    candidate_chunk_ids = models.JSONField(default=list)
    final_chunk_ids = models.JSONField(default=list)
    elapsed_ms = models.PositiveIntegerField(default=0)
    failure_kind = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
