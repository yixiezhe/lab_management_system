import json
import uuid
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from labops_agent.models import AgentConversation


@dataclass
class ConversationSession:
    id: uuid.UUID
    state: dict
    instance: object = None


class ConversationStateService:
    """Persist only compact, validated business slots for multi-turn edits."""

    TTL = timedelta(hours=24)
    PREPARE_TO_DOMAIN = {
        "prepare_procurement_request": "procurement",
        "prepare_equipment_reservation": "equipment",
    }

    def load_or_create(self, actor, conversation_id=None):
        if not getattr(actor, "is_authenticated", False) or not getattr(actor, "pk", None):
            return ConversationSession(uuid.uuid4(), {})

        now = timezone.now()
        conversation = None
        if conversation_id:
            conversation = (
                AgentConversation.objects.filter(
                    pk=conversation_id,
                    actor=actor,
                    expires_at__gt=now,
                )
                .only("id", "state", "expires_at")
                .first()
            )
        if conversation is None:
            conversation = AgentConversation.objects.create(
                actor=actor,
                state={},
                expires_at=now + self.TTL,
            )
        return ConversationSession(conversation.id, dict(conversation.state), conversation)

    @staticmethod
    def context_for_model(session):
        return dict(session.state or {})

    def remember_tool_result(self, session, name, arguments, result):
        domain = self.PREPARE_TO_DOMAIN.get(name)
        if not domain or not result.ok:
            return

        data = result.data if isinstance(result.data, dict) else {}
        action = data.get("action") if isinstance(data.get("action"), dict) else {}
        preview = action.get("preview") if isinstance(action.get("preview"), dict) else {}
        slots = preview or self._compact_arguments(domain, arguments)
        resolved = data.get("resolved")
        if isinstance(resolved, dict):
            slots = {**slots, **resolved}
        if not slots:
            return

        session.state = self._json_safe({
            "last_domain": domain,
            f"{domain}_draft": slots,
            "last_status": str(data.get("status") or "")[:40],
        })
        if session.instance is None:
            return
        session.instance.state = session.state
        session.instance.expires_at = timezone.now() + self.TTL
        session.instance.save(update_fields=["state", "expires_at", "updated_at"])

    @staticmethod
    def _compact_arguments(domain, arguments):
        if domain == "equipment":
            allowed = {
                "equipment_id",
                "equipment_query",
                "target_date",
                "start_time",
                "end_time",
                "duration_minutes",
                "position_no",
            }
            return {
                key: value
                for key, value in arguments.items()
                if key in allowed and value not in (None, "", [])
            }

        allowed = {"expense_type", "platform", "items"}
        return {
            key: value
            for key, value in arguments.items()
            if key in allowed and value not in (None, "", [])
        }

    @staticmethod
    def _json_safe(value):
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))
