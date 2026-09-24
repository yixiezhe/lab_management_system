import logging
import uuid
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError as DRFValidationError

from common_serializers.serializers import PurchaseRequestSerializer
from procurement.models import Platform, WhitelistItem

from labops_agent.models import AgentActionDraft
from .procurement_context import ProcurementContextService

logger = logging.getLogger(__name__)


class ProcurementActionService:
    DRAFT_TTL = timedelta(minutes=30)
    SPECIAL_SPEC_PLATFORMS = {"多多", "药代"}

    @staticmethod
    def _assert_admin(actor):
        if not (
            getattr(actor, "is_authenticated", False)
            and (
                getattr(actor, "is_superuser", False)
                or getattr(actor, "is_system_admin", False)
            )
        ):
            raise PermissionDenied("只有系统管理员可以准备或确认采购申请。")

    @staticmethod
    def _categories(whitelist_item):
        value = whitelist_item.main_category
        if isinstance(value, list):
            return {str(item) for item in value if item in {"public", "c2c"}}
        if value in {"public", "c2c"}:
            return {value}
        return set()

    @staticmethod
    def _text(value, fallback=""):
        value = fallback if value in (None, "") else value
        return str(value or "").strip()

    @staticmethod
    def _money(value):
        if value in (None, ""):
            return None
        try:
            result = Decimal(str(value)).quantize(Decimal("0.01"))
        except (InvalidOperation, TypeError, ValueError):
            return None
        return result if result > 0 else None

    @classmethod
    def _platform_choices(cls, expense_type):
        queryset = Platform.objects.all()
        if expense_type:
            queryset = queryset.filter(category=expense_type)
        return list(queryset.order_by("name").values_list("name", flat=True)[:30])

    @classmethod
    def _needs_information(cls, resolved, missing_fields, **extra):
        return {
            "status": "needs_information",
            "resolved": resolved,
            "missing_fields": missing_fields,
            **extra,
        }

    @classmethod
    def resolve(cls, args):
        raw_items = args.get("items") or []
        resolved = {
            "expense_type": args.get("expense_type"),
            "platform": cls._text(args.get("platform")) or None,
            "items": [],
        }
        if not raw_items:
            return cls._needs_information(resolved, ["items"])

        whitelist_rows = []
        unmatched = []
        context_service = ProcurementContextService()
        for index, raw_item in enumerate(raw_items):
            content = cls._text(raw_item.get("content"))
            whitelist_item = WhitelistItem.objects.filter(content__iexact=content).first()
            if not whitelist_item:
                candidates = context_service.search_candidates(content, limit=3) if content else []
                unmatched.append(
                    {
                        "index": index,
                        "content": content,
                        "candidates": [item["content"] for item in candidates],
                    }
                )
                continue
            whitelist_rows.append((raw_item, whitelist_item))

        if unmatched:
            missing = [f"items.{item['index']}.content" for item in unmatched]
            return cls._needs_information(
                resolved,
                missing,
                unmatched_items=unmatched,
                message="部分采购内容未能精确匹配白名单，请从候选项中确认。",
            )

        purchase_types = {row.purchase_type for _, row in whitelist_rows}
        if len(purchase_types) != 1:
            raise ValidationError("不同采购类型的物品请拆分为多份采购申请。")
        purchase_type = next(iter(purchase_types))

        specific_platforms = {
            cls._text(row.platform) for _, row in whitelist_rows if cls._text(row.platform)
        }
        if len(specific_platforms) > 1:
            raise ValidationError("属于不同采购平台的物品请拆分为多份采购申请。")

        platform_name = resolved["platform"]
        required_platform = next(iter(specific_platforms), None)
        if required_platform and platform_name and required_platform != platform_name:
            raise ValidationError(f"白名单规定这些物品必须使用“{required_platform}”平台。")
        platform_name = required_platform or platform_name
        platform_obj = Platform.objects.filter(name=platform_name).first() if platform_name else None

        category_sets = [cls._categories(row) for _, row in whitelist_rows]
        common_categories = set.intersection(*category_sets) if category_sets else set()
        if platform_obj:
            common_categories &= {platform_obj.category}

        requested_expense = args.get("expense_type")
        if requested_expense and requested_expense not in common_categories:
            raise ValidationError("所选经费类型与白名单或采购平台不一致。")
        expense_type = requested_expense
        if not expense_type and len(common_categories) == 1:
            expense_type = next(iter(common_categories))

        missing_fields = []
        if not expense_type:
            missing_fields.append("expense_type")
        if platform_name and not platform_obj:
            platform_name = None
        if not platform_name:
            missing_fields.append("platform")
        resolved["expense_type"] = expense_type
        resolved["platform"] = platform_name

        for index, (raw_item, whitelist_item) in enumerate(whitelist_rows):
            unit_price = cls._money(raw_item.get("unit_price"))
            quantity = raw_item.get("quantity")
            if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
                quantity = None
            item = {
                "purchase_type": purchase_type,
                "content": whitelist_item.content,
                "manufacturer": cls._text(raw_item.get("manufacturer"), whitelist_item.manufacturer),
                "parameters": cls._text(raw_item.get("parameters"), whitelist_item.parameters),
                "cas_number": cls._text(raw_item.get("cas_number"), whitelist_item.cas_number),
                "product_number": cls._text(raw_item.get("product_number"), whitelist_item.product_number),
                "purchase_link": cls._text(raw_item.get("purchase_link")),
                "specifications": cls._text(raw_item.get("specifications"), whitelist_item.specifications),
                "unit_price": str(unit_price) if unit_price else None,
                "quantity": quantity,
                "whitelist_id": whitelist_item.id,
            }
            if unit_price is None:
                missing_fields.append(f"items.{index}.unit_price")
            if quantity is None:
                missing_fields.append(f"items.{index}.quantity")
            if expense_type == "public" and not item["purchase_link"]:
                missing_fields.append(f"items.{index}.purchase_link")
            if platform_name in cls.SPECIAL_SPEC_PLATFORMS and not item["specifications"]:
                missing_fields.append(f"items.{index}.specifications")
            resolved["items"].append(item)

        choices = {
            "expense_type": sorted(common_categories),
            "platform": cls._platform_choices(expense_type),
        }
        if missing_fields:
            return cls._needs_information(
                resolved,
                missing_fields,
                choices=choices,
                message="采购规则已匹配，请补充缺失字段。",
            )

        payload_items = []
        sources = []
        total_price = Decimal("0.00")
        for item in resolved["items"]:
            clean_item = {key: value for key, value in item.items() if key != "whitelist_id"}
            payload_items.append(clean_item)
            total_price += Decimal(clean_item["unit_price"]) * clean_item["quantity"]
            sources.append({"type": "whitelist", "id": item["whitelist_id"], "title": item["content"]})
        payload = {
            "expense_type": expense_type,
            "platform": platform_name,
            "total_price": str(total_price.quantize(Decimal("0.01"))),
            "items": payload_items,
        }
        serializer = PurchaseRequestSerializer(data=payload)
        try:
            serializer.is_valid(raise_exception=True)
        except DRFValidationError as exc:
            return cls._needs_information(
                resolved,
                ["business_validation"],
                validation_errors=exc.detail,
                message="采购数据未通过现有业务校验。",
            )
        return {"status": "ready", "payload": payload, "sources": sources}

    @classmethod
    def prepare(cls, actor, args):
        cls._assert_admin(actor)
        result = cls.resolve(args)
        if result["status"] != "ready":
            return result
        expires_at = timezone.now() + cls.DRAFT_TTL
        draft = AgentActionDraft.objects.create(
            actor=actor,
            action_type=AgentActionDraft.ACTION_PROCUREMENT_CREATE,
            payload=result["payload"],
            resolution={"sources": result["sources"]},
            expires_at=expires_at,
        )
        return {
            "status": "ready",
            "message": "采购申请草稿已准备好，必须由用户点击确认后才会提交。",
            "action": cls._action_payload(draft),
        }

    @classmethod
    def prepare_prefill(cls, actor, args):
        """Prepare a client-side form draft without creating a business record."""
        cls._assert_admin(actor)
        result = cls.resolve(args)
        if result["status"] != "ready":
            return result
        payload = result["payload"]
        return {
            "status": "ready",
            "message": "采购信息已校验，可打开原采购页面预填；最终提交仍由用户完成。",
            "action": {
                "id": f"procurement-prefill-{uuid.uuid4().hex}",
                "type": "procurement_form_prefill",
                "status": "pending_user_submit",
                "title": "预填采购申请",
                "confirm_label": "打开采购页面并预填",
                "preview": {
                    "expense_type": payload["expense_type"],
                    "expense_type_label": (
                        "公共经费" if payload["expense_type"] == "public" else "公对公"
                    ),
                    "platform": payload["platform"],
                    "total_price": payload["total_price"],
                    "items": payload["items"],
                },
                "sources": result["sources"],
            },
        }

    @classmethod
    def _action_payload(cls, draft):
        payload = draft.payload
        return {
            "id": str(draft.id),
            "type": draft.action_type,
            "status": "pending_confirmation",
            "title": "提交采购申请",
            "confirm_label": "确认提交",
            "expires_at": draft.expires_at.isoformat(),
            "preview": {
                "expense_type": payload["expense_type"],
                "expense_type_label": "公共经费" if payload["expense_type"] == "public" else "公对公",
                "platform": payload["platform"],
                "total_price": payload["total_price"],
                "items": payload["items"],
            },
            "sources": draft.resolution.get("sources", []),
        }

    @classmethod
    @transaction.atomic
    def confirm(cls, actor, draft_id):
        cls._assert_admin(actor)
        draft = (
            AgentActionDraft.objects.select_for_update()
            .filter(actor=actor, action_type=AgentActionDraft.ACTION_PROCUREMENT_CREATE)
            .get(pk=draft_id)
        )
        if draft.status == AgentActionDraft.STATUS_CONFIRMED:
            return cls._confirmed_payload(draft)
        if draft.status != AgentActionDraft.STATUS_PENDING:
            raise ValidationError("该操作已失效，不能再次提交。")
        if draft.expires_at <= timezone.now():
            draft.status = AgentActionDraft.STATUS_EXPIRED
            draft.save(update_fields=["status", "updated_at"])
            raise ValidationError("采购草稿已过期，请重新生成。")

        fresh = cls.resolve(draft.payload)
        if fresh["status"] != "ready":
            raise ValidationError("白名单或采购规则已变化，请重新生成草稿。")
        serializer = PurchaseRequestSerializer(data=fresh["payload"])
        serializer.is_valid(raise_exception=True)
        purchase_request = serializer.save(applicant=actor)

        draft.status = AgentActionDraft.STATUS_CONFIRMED
        draft.target_object_id = purchase_request.id
        draft.confirmed_at = timezone.now()
        draft.save(update_fields=["status", "target_object_id", "confirmed_at", "updated_at"])
        logger.info(
            "labops_agent action_confirmed draft=%s action=%s target=%s",
            draft.id,
            draft.action_type,
            purchase_request.id,
        )
        return cls._confirmed_payload(draft, purchase_request)

    @staticmethod
    def _confirmed_payload(draft, purchase_request=None):
        if purchase_request is None:
            from procurement.models import PurchaseRequest

            try:
                purchase_request = PurchaseRequest.objects.get(pk=draft.target_object_id)
            except ObjectDoesNotExist:
                raise ValidationError("已提交的采购记录不存在。")
        return {
            "id": str(draft.id),
            "type": draft.action_type,
            "status": "confirmed",
            "target": {
                "id": purchase_request.id,
                "status": purchase_request.status,
                "expense_type": purchase_request.expense_type,
                "platform": purchase_request.platform,
                "total_price": str(purchase_request.total_price),
            },
        }
