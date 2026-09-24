from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from labops_agent.models import AgentActionDraft
from labops_agent.services import ProcurementActionService, ProcurementContextService
from procurement.models import Platform, PurchaseRequest, WhitelistItem
from users.models import UserProfile


class ProcurementActionServiceTests(TestCase):
    def setUp(self):
        self.admin = UserProfile.objects.create_superuser(
            username="draft-admin",
            password="test-pass-123",
            email="draft-admin@example.com",
            name="草稿管理员",
        )
        self.platform = Platform.objects.create(
            name="测试公共平台",
            prefix="Z",
            category="public",
        )
        self.whitelist = WhitelistItem.objects.create(
            content="无水乙醇",
            main_category=["public"],
            platform=self.platform.name,
            purchase_type="chemical",
            manufacturer="测试厂商",
            specifications="500mL",
        )
        self.client = APIClient()

    def args(self, **item_overrides):
        item = {
            "content": "无水乙醇",
            "purchase_type": None,
            "manufacturer": None,
            "parameters": None,
            "cas_number": None,
            "product_number": None,
            "purchase_link": "https://example.com/item",
            "specifications": None,
            "unit_price": "80.00",
            "quantity": 5,
        }
        item.update(item_overrides)
        return {"expense_type": None, "platform": None, "items": [item]}

    def test_prefetch_returns_only_relevant_whitelist_context(self):
        context = ProcurementContextService().prefetch("我要采购5瓶无水乙醇")

        self.assertEqual(context["whitelist_candidates"][0]["id"], self.whitelist.id)
        self.assertEqual(context["whitelist_candidates"][0]["platform"], self.platform.name)

    def test_missing_required_field_does_not_create_draft(self):
        result = ProcurementActionService.prepare(
            self.admin,
            self.args(purchase_link=None),
        )

        self.assertEqual(result["status"], "needs_information")
        self.assertIn("items.0.purchase_link", result["missing_fields"])
        self.assertFalse(AgentActionDraft.objects.exists())

    def test_whitelist_rules_prepare_ready_draft(self):
        result = ProcurementActionService.prepare(self.admin, self.args())

        self.assertEqual(result["status"], "ready")
        preview = result["action"]["preview"]
        self.assertEqual(preview["expense_type"], "public")
        self.assertEqual(preview["platform"], self.platform.name)
        self.assertEqual(preview["total_price"], "400.00")
        self.assertEqual(preview["items"][0]["manufacturer"], "测试厂商")

    def test_form_prefill_does_not_create_action_or_purchase_record(self):
        result = ProcurementActionService.prepare_prefill(self.admin, self.args())

        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["action"]["type"], "procurement_form_prefill")
        self.assertEqual(result["action"]["preview"]["platform"], self.platform.name)
        self.assertFalse(AgentActionDraft.objects.exists())
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_confirm_reuses_business_serializer_and_is_idempotent(self):
        prepared = ProcurementActionService.prepare(self.admin, self.args())
        draft_id = prepared["action"]["id"]

        first = ProcurementActionService.confirm(self.admin, draft_id)
        second = ProcurementActionService.confirm(self.admin, draft_id)

        self.assertEqual(first["status"], "confirmed")
        self.assertEqual(second["target"]["id"], first["target"]["id"])
        self.assertEqual(PurchaseRequest.objects.count(), 1)
        request = PurchaseRequest.objects.get()
        self.assertEqual(request.applicant, self.admin)
        self.assertEqual(request.items.get().original_applicant, self.admin)

    def test_conflicting_platform_is_rejected(self):
        Platform.objects.create(name="其他平台", prefix="Y", category="public")
        args = self.args()
        args["platform"] = "其他平台"

        with self.assertRaisesMessage(ValidationError, "白名单规定"):
            ProcurementActionService.prepare(self.admin, args)

    def test_confirm_endpoint_requires_explicit_authenticated_click(self):
        prepared = ProcurementActionService.prepare(self.admin, self.args())
        draft_id = prepared["action"]["id"]
        url = reverse("labops-agent-action-confirm", kwargs={"draft_id": draft_id})

        denied = self.client.post(url, format="json")
        self.client.force_authenticate(self.admin)
        confirmed = self.client.post(url, format="json")

        self.assertEqual(denied.status_code, 401)
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.data["action"]["status"], "confirmed")
        self.assertEqual(PurchaseRequest.objects.count(), 1)
