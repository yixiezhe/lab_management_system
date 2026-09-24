from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from procurement.models import PurchaseRequest
from procurement.services import ProcurementQueryService
from users.models import Role, UserProfile


class ProcurementQueryServiceTests(TestCase):
    def setUp(self):
        self.tutor_role = Role.objects.create(name="导师用户")
        self.admin_role = Role.objects.create(name="系统管理员")
        self.land_role = Role.objects.create(name="land设备主机")

        self.tutor = self.create_user("tutor", "导师")
        self.tutor.roles.add(self.tutor_role)
        self.student = self.create_user("student", "学生", assigned_tutor=self.tutor)
        self.other = self.create_user("other", "其他成员")
        self.admin = self.create_user("admin", "管理员")
        self.admin.roles.add(self.admin_role)
        self.land_host = self.create_user("land", "设备主机")
        self.land_host.roles.add(self.land_role)

        self.student_request = self.create_request(
            self.student,
            order_number="P2026090101",
            status="paid",
        )
        self.other_request = self.create_request(
            self.other,
            order_number="P2026090102",
            status="pending",
        )

    @staticmethod
    def create_user(username, name, assigned_tutor=None):
        return UserProfile.objects.create_user(
            username=username,
            password="test-pass-123",
            name=name,
            email=f"{username}@example.com",
            assigned_tutor=assigned_tutor,
        )

    @staticmethod
    def create_request(applicant, *, order_number, status):
        return PurchaseRequest.objects.create(
            applicant=applicant,
            expense_type="public",
            platform="测试平台",
            order_number=order_number,
            total_price=Decimal("123.45"),
            status=status,
        )

    def test_member_only_sees_own_requests(self):
        rows = ProcurementQueryService.list_requests(self.student)
        self.assertEqual([row["id"] for row in rows], [self.student_request.id])

        with self.assertRaises(PurchaseRequest.DoesNotExist):
            ProcurementQueryService.get_request(
                self.student,
                request_id=self.other_request.id,
            )

    def test_tutor_only_sees_self_and_assigned_students(self):
        own_request = self.create_request(
            self.tutor,
            order_number="P2026090103",
            status="pending",
        )
        rows = ProcurementQueryService.list_requests(self.tutor)
        self.assertEqual(
            {row["id"] for row in rows},
            {self.student_request.id, own_request.id},
        )

    def test_system_admin_can_see_all_requests(self):
        rows = ProcurementQueryService.list_requests(self.admin)
        self.assertEqual(
            {row["id"] for row in rows},
            {self.student_request.id, self.other_request.id},
        )

    def test_land_host_is_rejected(self):
        with self.assertRaises(PermissionDenied):
            ProcurementQueryService.list_requests(self.land_host)

    def test_filters_and_serializes_next_step(self):
        rows = ProcurementQueryService.list_requests(
            self.student,
            expense_type="public",
            statuses=["paid"],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status_label"], "待收货")
        self.assertEqual(rows[0]["next_step"]["action"], "confirm_goods_received")
        self.assertEqual(rows[0]["total_price"], "123.45")

    def test_request_lookup_requires_exactly_one_identifier(self):
        with self.assertRaisesMessage(ValidationError, "必须且只能提供"):
            ProcurementQueryService.get_request(self.student)
        with self.assertRaisesMessage(ValidationError, "必须且只能提供"):
            ProcurementQueryService.get_request(
                self.student,
                request_id=self.student_request.id,
                order_number=self.student_request.order_number,
            )
