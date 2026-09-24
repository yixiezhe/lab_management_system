import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="AgentActionDraft",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action_type", models.CharField(choices=[("procurement_create", "创建采购申请")], max_length=40)),
                ("status", models.CharField(choices=[("pending", "待确认"), ("confirmed", "已确认"), ("expired", "已过期"), ("cancelled", "已取消")], db_index=True, default="pending", max_length=20)),
                ("payload", models.JSONField(default=dict)),
                ("resolution", models.JSONField(default=dict)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("target_object_id", models.PositiveBigIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="agent_action_drafts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="agentactiondraft",
            index=models.Index(fields=["actor", "status", "action_type"], name="labops_actor_status_type_idx"),
        ),
    ]
