import logging
from collections import Counter
from dataclasses import dataclass

from django.core.exceptions import (
    ObjectDoesNotExist,
    PermissionDenied,
    ValidationError as DjangoValidationError,
)

from equipment.services.query_service import EquipmentQueryService
from procurement.services.query_service import ProcurementQueryService
from rest_framework.exceptions import ValidationError as DRFValidationError

from labops_agent.serializers import (
    AvailableSlotsArgs,
    EquipmentReservationDraftArgs,
    EquipmentSearchArgs,
    MyReservationsArgs,
    ProcurementDetailArgs,
    ProcurementDraftArgs,
    ProcurementListArgs,
    ReservationConflictArgs,
)
from labops_agent.services import EquipmentReservationActionService, ProcurementActionService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolExecutionResult:
    name: str
    domain: str
    ok: bool
    data: object = None
    error_code: str = ""
    error_message: str = ""

    def for_model(self):
        if self.ok:
            return {"ok": True, "data": self.data}
        return {
            "ok": False,
            "error": {
                "code": self.error_code,
                "message": self.error_message,
            },
        }

    def trace(self):
        return {"name": self.name, "status": "success" if self.ok else "error"}

    def action(self):
        if not self.ok or not isinstance(self.data, dict):
            return None
        value = self.data.get("action")
        return value if isinstance(value, dict) else None


@dataclass(frozen=True)
class ToolBinding:
    domain: str
    serializer_class: object
    handler: object
    sanitizer: object


def _procurement_list(actor, args):
    return ProcurementQueryService.list_requests(
        actor,
        expense_type=args.get("expense_type"),
        statuses=args.get("statuses"),
        limit=args.get("limit", 10),
    )


def _procurement_detail(actor, args):
    return ProcurementQueryService.get_request(
        actor,
        request_id=args.get("request_id"),
        order_number=args.get("order_number"),
    )


def _procurement_prepare(actor, args):
    return ProcurementActionService.prepare_prefill(actor, args)


def _equipment_search(actor, args):
    return EquipmentQueryService.search_equipment(
        actor,
        query=args.get("query", ""),
        active_only=args.get("active_only", True),
        limit=args.get("limit", 10),
    )


def _equipment_prepare(actor, args):
    return EquipmentReservationActionService.prepare(actor, args)


def _my_reservations(actor, args):
    return EquipmentQueryService.get_my_reservations(
        actor,
        upcoming=args.get("upcoming"),
        start_date=args.get("start_date"),
        end_date=args.get("end_date"),
        statuses=args.get("statuses"),
        limit=args.get("limit", 20),
    )


def _available_slots(actor, args):
    return EquipmentQueryService.get_available_slots(actor, **args)


def _reservation_conflict(actor, args):
    return EquipmentQueryService.check_reservation_conflict(actor, **args)


def _compact_procurement(value):
    def compact(row):
        applicant = row.get("applicant") or {}
        return {
            "id": row.get("id"),
            "order_number": row.get("order_number"),
            "request_date": row.get("request_date"),
            "applicant_name": applicant.get("name"),
            "merged_applicant_names": row.get("merged_applicant_names", []),
            "expense_type_label": row.get("expense_type_label"),
            "platform": row.get("platform"),
            "status": row.get("status"),
            "status_label": row.get("status_label"),
            "rejection_reason": row.get("rejection_reason"),
            "total_price": row.get("total_price"),
            "actual_payment_amount": row.get("actual_payment_amount"),
            "item_count": row.get("item_count"),
            "next_step": row.get("next_step"),
        }

    if isinstance(value, list):
        return [compact(row) for row in value]
    return compact(value)


def _compact_equipment(rows):
    compacted = []
    for row in rows:
        description = row.get("description") or ""
        compacted.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "location": row.get("location"),
                "description": description[:300],
                "booking_mode": row.get("booking_mode"),
                "booking_mode_label": row.get("booking_mode_label"),
                "time_unit_minutes": row.get("time_unit_minutes"),
                "open_time_start": row.get("open_time_start"),
                "open_time_end": row.get("open_time_end"),
                "effective_max_advance_days": row.get("effective_max_advance_days"),
            }
        )
    return compacted


def _compact_slots(result):
    available = []
    blocked_reasons = Counter()
    for slot in result.get("slots", []):
        if slot.get("available"):
            available.append(
                {
                    key: slot.get(key)
                    for key in (
                        "start",
                        "end",
                        "available_positions",
                        "locked_rotation_speed_rpm",
                    )
                    if slot.get(key) is not None
                }
            )
        else:
            blocked_reasons[slot.get("reason") or "unavailable"] += 1
    equipment = result.get("equipment") or {}
    return {
        "equipment": {"id": equipment.get("id"), "name": equipment.get("name")},
        "date": result.get("date"),
        "latest_bookable_date": result.get("latest_bookable_date"),
        "position_no": result.get("position_no"),
        "available_slots": available[:96],
        "available_slots_truncated": len(available) > 96,
        "blocked_slot_summary": dict(blocked_reasons),
    }


def _identity(value):
    return value


class ToolRegistry:
    def __init__(self):
        self.bindings = {
            "list_procurement_requests": ToolBinding(
                "procurement", ProcurementListArgs, _procurement_list, _compact_procurement
            ),
            "get_procurement_request": ToolBinding(
                "procurement",
                ProcurementDetailArgs,
                _procurement_detail,
                _compact_procurement,
            ),
            "prepare_procurement_request": ToolBinding(
                "procurement",
                ProcurementDraftArgs,
                _procurement_prepare,
                _identity,
            ),
            "search_equipment": ToolBinding(
                "equipment", EquipmentSearchArgs, _equipment_search, _compact_equipment
            ),
            "prepare_equipment_reservation": ToolBinding(
                "equipment",
                EquipmentReservationDraftArgs,
                _equipment_prepare,
                _identity,
            ),
            "get_my_reservations": ToolBinding(
                "equipment", MyReservationsArgs, _my_reservations, _identity
            ),
            "get_available_slots": ToolBinding(
                "equipment", AvailableSlotsArgs, _available_slots, _compact_slots
            ),
            "check_reservation_conflict": ToolBinding(
                "equipment",
                ReservationConflictArgs,
                _reservation_conflict,
                _identity,
            ),
        }

    def execute(self, name, arguments, actor):
        binding = self.bindings.get(name)
        if binding is None:
            return ToolExecutionResult(
                name=name,
                domain="unsupported",
                ok=False,
                error_code="unknown_tool",
                error_message="模型选择了系统未开放的工具。",
            )

        serializer = binding.serializer_class(data=arguments)
        if not serializer.is_valid():
            return ToolExecutionResult(
                name=name,
                domain=binding.domain,
                ok=False,
                error_code="invalid_arguments",
                error_message=str(serializer.errors)[:500],
            )
        try:
            result = binding.handler(actor, serializer.validated_data)
            result = binding.sanitizer(result)
        except PermissionDenied:
            return ToolExecutionResult(
                name=name,
                domain=binding.domain,
                ok=False,
                error_code="permission_denied",
                error_message="当前账号无权执行该查询。",
            )
        except ObjectDoesNotExist:
            return ToolExecutionResult(
                name=name,
                domain=binding.domain,
                ok=False,
                error_code="not_found",
                error_message="未找到有权查看的记录。",
            )
        except (DjangoValidationError, DRFValidationError) as exc:
            message = "; ".join(getattr(exc, "messages", []) or [str(exc)])
            return ToolExecutionResult(
                name=name,
                domain=binding.domain,
                ok=False,
                error_code="validation_error",
                error_message=message[:500],
            )
        except Exception:
            logger.exception("LabOps tool execution failed: %s", name)
            return ToolExecutionResult(
                name=name,
                domain=binding.domain,
                ok=False,
                error_code="internal_error",
                error_message="业务查询暂时失败。",
            )

        return ToolExecutionResult(
            name=name,
            domain=binding.domain,
            ok=True,
            data=result,
        )
