import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("labops_agent", "0002_agentconversation"),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("domain", models.CharField(choices=[("procurement", "采购"), ("equipment", "仪器")], db_index=True, max_length=30)),
                ("source_type", models.CharField(default="markdown", max_length=30)),
                ("source_path", models.CharField(max_length=500)),
                ("source_url", models.CharField(blank=True, default="", max_length=500)),
                ("visibility", models.CharField(choices=[("admin", "仅管理员"), ("public", "公开")], db_index=True, default="admin", max_length=20)),
                ("version", models.CharField(max_length=80)),
                ("checksum", models.CharField(db_index=True, max_length=64)),
                ("status", models.CharField(choices=[("draft", "草稿"), ("indexing", "索引中"), ("published", "已发布"), ("failed", "失败"), ("archived", "已归档")], db_index=True, default="draft", max_length=20)),
                ("effective_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("parser_version", models.CharField(default="labops-parser-v1", max_length=80)),
                ("embedding_version", models.CharField(default="", max_length=120)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_knowledge_documents", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-updated_at"]},
        ),
        migrations.CreateModel(
            name="KnowledgeChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_index", models.PositiveIntegerField()),
                ("section_path", models.CharField(blank=True, default="", max_length=500)),
                ("content", models.TextField()),
                ("content_hash", models.CharField(db_index=True, max_length=64)),
                ("char_count", models.PositiveIntegerField(default=0)),
                ("token_estimate", models.PositiveIntegerField(default=0)),
                ("vector_point_id", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chunks", to="labops_agent.knowledgedocument")),
            ],
            options={"ordering": ["document_id", "chunk_index"]},
        ),
        migrations.CreateModel(
            name="KnowledgeIngestionJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_path", models.CharField(max_length=500)),
                ("status", models.CharField(choices=[("running", "执行中"), ("succeeded", "成功"), ("failed", "失败"), ("dry_run", "仅检查")], db_index=True, max_length=20)),
                ("chunk_count", models.PositiveIntegerField(default=0)),
                ("error_summary", models.CharField(blank=True, default="", max_length=500)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="knowledge_ingestion_jobs", to=settings.AUTH_USER_MODEL)),
                ("document", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ingestion_jobs", to="labops_agent.knowledgedocument")),
            ],
        ),
        migrations.CreateModel(
            name="KnowledgeRetrievalLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("request_id", models.CharField(db_index=True, max_length=64)),
                ("domain", models.CharField(blank=True, default="", max_length=30)),
                ("route", models.CharField(default="rag", max_length=40)),
                ("status", models.CharField(db_index=True, max_length=30)),
                ("candidate_chunk_ids", models.JSONField(default=list)),
                ("final_chunk_ids", models.JSONField(default=list)),
                ("elapsed_ms", models.PositiveIntegerField(default=0)),
                ("failure_kind", models.CharField(blank=True, default="", max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="knowledge_retrieval_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="knowledgedocument",
            constraint=models.UniqueConstraint(fields=("domain", "source_path", "version"), name="labops_knowledge_source_version_uniq"),
        ),
        migrations.AddConstraint(
            model_name="knowledgechunk",
            constraint=models.UniqueConstraint(fields=("document", "chunk_index"), name="labops_knowledge_document_chunk_uniq"),
        ),
    ]
