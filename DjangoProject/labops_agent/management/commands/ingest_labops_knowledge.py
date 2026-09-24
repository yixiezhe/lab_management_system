from django.core.management.base import BaseCommand, CommandError

from labops_agent.models import KnowledgeDocument
from labops_agent.rag.ingestion import KnowledgeIngestionService


class Command(BaseCommand):
    help = "解析并索引 LabOps 采购或仪器知识文档"

    def add_arguments(self, parser):
        parser.add_argument("--path", required=True)
        parser.add_argument("--title", required=True)
        parser.add_argument(
            "--domain",
            required=True,
            choices=[
                KnowledgeDocument.DOMAIN_PROCUREMENT,
                KnowledgeDocument.DOMAIN_EQUIPMENT,
            ],
        )
        parser.add_argument("--document-version", required=True)
        parser.add_argument(
            "--visibility",
            default=KnowledgeDocument.VISIBILITY_ADMIN,
            choices=[
                KnowledgeDocument.VISIBILITY_ADMIN,
                KnowledgeDocument.VISIBILITY_PUBLIC,
            ],
        )
        parser.add_argument("--source-url", default="")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        try:
            result = KnowledgeIngestionService().ingest(
                options["path"],
                title=options["title"],
                domain=options["domain"],
                version=options["document_version"],
                visibility=options["visibility"],
                source_url=options["source_url"],
                dry_run=options["dry_run"],
            )
        except Exception as exc:
            raise CommandError(str(exc)) from exc
        action = "跳过（内容未变）" if result.skipped else result.status
        self.stdout.write(
            self.style.SUCCESS(
                f"{action}: document={result.document_id}, chunks={result.chunk_count}, "
                f"checksum={result.checksum}"
            )
        )
