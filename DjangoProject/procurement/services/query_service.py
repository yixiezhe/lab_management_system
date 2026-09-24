from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q

from procurement.models import PurchaseRequest


class ProcurementQueryService:
    """Read-only procurement queries for authenticated business actors."""

    MAX_LIST_LIMIT = 100
    ALLOWED_EXPENSE_TYPES = {"public", "c2c"}
    ALLOWED_STATUSES = {value for value, _ in PurchaseRequest.STATUS_CHOICES}

    STATUS_GUIDANCE = {
        "pending": ("wait_for_approval", "申请正在等待审批。"),
        "rejected": ("revise_and_resubmit", "查看驳回原因，修改后重新提交。"),
        "withdrawn": ("create_if_needed", "申请已撤回；如仍需采购，请重新申请。"),
        "payment_rejected": ("review_payment_issue", "查看付款驳回原因并等待处理。"),
        "pending_purchase_order": ("wait_for_purchase_order", "等待请购流程处理。"),
        "pending_contract": ("wait_for_contract", "等待合同流程处理。"),
        "approved": ("wait_for_payment", "申请已审批，等待支付。"),
        "paid": ("confirm_goods_received", "支付完成后，收到货物时提交收货信息。"),
        "goods_received": ("submit_invoice", "货物已确认收到，下一步需要提交发票。"),
        "invoiced": ("wait_for_inspection", "发票已提交，等待验收。"),
        "accepted": ("wait_for_reimbursement", "验收完成，等待报销。"),
        "inspection_skipped": ("wait_for_reimbursement", "无需验收，等待报销。"),
        "reimbursed": ("wait_for_completion", "报销已完成，等待流程归档。"),
        "merged": ("view_parent_request", "申请已合并，请查看合并后的主申请。"),
        "completed": ("none", "采购流程已完成。"),
    }

    @classmethod
    def visible_requests(cls, actor):
        """Return the requests visible to an actor without revealing hidden rows."""
        roles = cls._require_actor(actor)
        queryset = (
            PurchaseRequest.objects.filter(parent_request__isnull=True)
            .select_related("applicant", "applicant__assigned_tutor", "handler")
            .prefetch_related(
                "items",
                "merged_children",
                "merged_children__applicant",
                "merged_children__items",
            )
        )

        if actor.is_superuser or "系统管理员" in roles:
            return queryset

        scope = Q(applicant=actor) | Q(merged_children__applicant=actor)
        if "导师用户" in roles:
            scope |= Q(applicant__assigned_tutor=actor)
            scope |= Q(merged_children__applicant__assigned_tutor=actor)
        return queryset.filter(scope).distinct()

    @classmethod
    def list_requests(
        cls,
        actor,
        *,
        expense_type=None,
        statuses=None,
        limit=20,
    ):
        queryset = cls.visible_requests(actor)
        if expense_type is not None:
            if expense_type not in cls.ALLOWED_EXPENSE_TYPES:
                raise ValidationError("不支持的采购经费类型。")
            queryset = queryset.filter(expense_type=expense_type)

        if statuses:
            normalized_statuses = set(statuses)
            unknown = normalized_statuses - cls.ALLOWED_STATUSES
            if unknown:
                raise ValidationError(f"不支持的采购状态：{', '.join(sorted(unknown))}")
            queryset = queryset.filter(status__in=normalized_statuses)

        normalized_limit = cls._normalize_limit(limit)
        queryset = queryset.order_by("-request_date", "-id")[:normalized_limit]
        return [cls._serialize_request(request) for request in queryset]

    @classmethod
    def get_request(cls, actor, *, request_id=None, order_number=None):
        if (request_id is None) == (order_number is None):
            raise ValidationError("必须且只能提供 request_id 或 order_number。")

        queryset = cls.visible_requests(actor)
        if request_id is not None:
            request = queryset.get(pk=request_id)
        else:
            request = queryset.get(order_number=order_number)
        return cls._serialize_request(request)

    @classmethod
    def _require_actor(cls, actor):
        if not actor or not getattr(actor, "is_authenticated", False):
            raise PermissionDenied("需要登录后才能查询采购申请。")
        roles = set(actor.roles.values_list("name", flat=True))
        if "land设备主机" in roles:
            raise PermissionDenied("设备主机账号不能查询采购申请。")
        return roles

    @classmethod
    def _normalize_limit(cls, limit):
        try:
            normalized = int(limit)
        except (TypeError, ValueError):
            raise ValidationError("limit 必须是整数。")
        if normalized < 1:
            raise ValidationError("limit 必须大于 0。")
        return min(normalized, cls.MAX_LIST_LIMIT)

    @classmethod
    def _serialize_request(cls, request):
        action, guidance = cls.STATUS_GUIDANCE.get(
            request.status,
            ("unknown", "当前状态暂无明确的下一步说明。"),
        )
        merged_applicants = sorted(
            {
                child.applicant.name
                for child in request.merged_children.all()
                if child.applicant_id
            }
        )
        return {
            "id": request.id,
            "order_number": request.order_number,
            "request_date": request.request_date.isoformat(),
            "applicant": {
                "id": request.applicant_id,
                "name": request.applicant.name,
            },
            "merged_applicant_names": merged_applicants,
            "expense_type": request.expense_type,
            "expense_type_label": request.get_expense_type_display(),
            "platform": request.platform,
            "status": request.status,
            "status_label": request.get_status_display(),
            "rejection_reason": request.rejection_reason,
            "total_price": str(request.total_price),
            "actual_payment_amount": (
                str(request.actual_payment_amount)
                if request.actual_payment_amount is not None
                else None
            ),
            "item_count": request.items.count(),
            "next_step": {
                "action": action,
                "guidance": guidance,
            },
        }
