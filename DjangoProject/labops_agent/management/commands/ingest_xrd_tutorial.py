from tempfile import NamedTemporaryFile

from django.core.management.base import BaseCommand, CommandError

from equipment.models import Equipment
from labops_agent.rag.ingestion import KnowledgeIngestionService


class Command(BaseCommand):
    help = "从本地数据库提取并索引 XRD 教程"

    def add_arguments(self, parser):
        parser.add_argument("--document-version", required=True)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        equipment = (
            Equipment.objects.filter(booking_mode=Equipment.BOOKING_MODE_XRD)
            .exclude(xrd_tutorial_html="")
            .order_by("id")
            .first()
        )
        if equipment is None:
            raise CommandError("本地数据库没有可用的 XRD 教程。")
        with NamedTemporaryFile(
            mode="w", suffix=".html", encoding="utf-8", delete=True
        ) as handle:
            handle.write(equipment.xrd_tutorial_html)
            handle.flush()
            try:
                result = KnowledgeIngestionService().ingest(
                    handle.name,
                    title=f"{equipment.name}操作教程",
                    domain="equipment",
                    version=options["document_version"],
                    visibility="admin",
                    source_url=f"/api/equipment/{equipment.id}/",
                    source_identity=f"db://equipment/{equipment.id}/xrd_tutorial_html",
                    dry_run=options["dry_run"],
                )
            except Exception as exc:
                raise CommandError(str(exc)) from exc
        self.stdout.write(
            self.style.SUCCESS(
                f"{result.status}: document={result.document_id}, chunks={result.chunk_count}"
            )
        )
