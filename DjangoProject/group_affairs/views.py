from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import UserProfile

from .models import (
    GroupAffairAdmin,
    GroupAffairBoard,
    GroupAffairDutyReminderRead,
    GroupAffairNotice,
    GroupAffairNoticeRead,
    GroupPurchase,
    GroupPurchasePopupRead,
)
from .serializers import GroupAffairBoardSerializer, GroupAffairNoticeSerializer, GroupPurchaseSerializer, WEEKDAY_LABELS
from .services import (
    can_manage_board,
    ensure_boards_for_all_tutors,
    get_group_members_queryset,
    get_or_create_board_for_tutor,
    get_user_group_tutor,
    is_group_member,
    is_land_host,
    is_system_admin,
)


class GroupAffairBoardViewSet(viewsets.ModelViewSet):
    serializer_class = GroupAffairBoardSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        base_queryset = (
            GroupAffairBoard.objects
            .select_related("tutor", "updated_by")
            .prefetch_related("tutor__roles")
        )

        if is_land_host(user):
            return base_queryset.none()

        if is_system_admin(user):
            ensure_boards_for_all_tutors()
            return base_queryset.all()

        tutor = get_user_group_tutor(user)
        if not tutor:
            return base_queryset.none()

        board, _ = get_or_create_board_for_tutor(tutor)
        return base_queryset.filter(pk=board.pk)

    def create(self, request, *args, **kwargs):
        return Response({"detail": "小组事务板由系统按导师自动创建。"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response({"detail": "小组事务板不能删除。"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        if not can_manage_board(request.user, instance):
            return Response({"detail": "只有系统管理员或本组小组管理员可以修改小组事务。"}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="admins")
    def add_admin(self, request, pk=None):
        board = self.get_object()
        if not can_manage_board(request.user, board):
            return Response({"detail": "只有系统管理员或本组小组管理员可以任命小组管理员。"}, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"user_id": ["请选择要任命的成员。"]}, status=status.HTTP_400_BAD_REQUEST)

        target_user = get_object_or_404(UserProfile, pk=user_id)
        if not is_group_member(target_user, board.tutor):
            return Response({"detail": "只能任命本小组成员为小组管理员。"}, status=status.HTTP_400_BAD_REQUEST)
        if target_user.id == board.tutor_id:
            serializer = self.get_serializer(board)
            return Response(serializer.data, status=status.HTTP_200_OK)

        GroupAffairAdmin.objects.get_or_create(
            tutor=board.tutor,
            user=target_user,
            defaults={"assigned_by": request.user},
        )
        serializer = self.get_serializer(board)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["delete"], url_path=r"admins/(?P<user_id>\d+)")
    def remove_admin(self, request, pk=None, user_id=None):
        board = self.get_object()
        if not can_manage_board(request.user, board):
            return Response({"detail": "只有系统管理员或本组小组管理员可以移除小组管理员。"}, status=status.HTTP_403_FORBIDDEN)

        if int(user_id) == board.tutor_id:
            return Response({"detail": "导师是默认小组管理员，不能移除。"}, status=status.HTTP_400_BAD_REQUEST)

        GroupAffairAdmin.objects.filter(tutor=board.tutor, user_id=user_id).delete()
        serializer = self.get_serializer(board)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"], url_path="notices")
    def notices(self, request, pk=None):
        board = self.get_object()
        if request.method == "GET":
            notices = (
                GroupAffairNotice.objects
                .filter(board=board)
                .select_related("board", "board__tutor", "created_by")
                .order_by("-created_at", "-id")[:30]
            )
            serializer = GroupAffairNoticeSerializer(notices, many=True, context={"request": request})
            return Response(serializer.data)

        if not can_manage_board(request.user, board):
            return Response({"detail": "只有系统管理员或本组小组管理员可以发布组内提醒。"}, status=status.HTTP_403_FORBIDDEN)

        serializer = GroupAffairNoticeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(board=board, created_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path=r"notices/(?P<notice_id>\d+)/mark-read")
    def mark_notice_read(self, request, pk=None, notice_id=None):
        board = self.get_object()
        notice = get_object_or_404(GroupAffairNotice, pk=notice_id, board=board)
        read_record, _ = GroupAffairNoticeRead.objects.update_or_create(
            notice=notice,
            user=request.user,
            defaults={"read_at": timezone.now()},
        )
        return Response({"id": notice.id, "read_at": read_record.read_at}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get", "post"], url_path="purchases")
    def purchases(self, request, pk=None):
        board = self.get_object()
        if request.method == "GET":
            queryset = board.purchases.select_related("requester", "buyer").all()
            return Response(GroupPurchaseSerializer(queryset, many=True, context={"request": request}).data)

        serializer = GroupPurchaseSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            locked_board = GroupAffairBoard.objects.select_for_update().get(pk=board.pk)
            rotation = [int(item) for item in (locked_board.purchase_rotation or [])]
            member_ids = set(get_group_members_queryset(locked_board.tutor).values_list("id", flat=True))
            rotation = [user_id for user_id in rotation if user_id in member_ids]
            if not rotation:
                return Response({"detail": "本组尚未设置采购轮班名单，请联系小组管理员。"}, status=status.HTTP_400_BAD_REQUEST)
            index = locked_board.purchase_rotation_index % len(rotation)
            buyer = get_object_or_404(UserProfile, pk=rotation[index])
            purchase = serializer.save(board=locked_board, requester=request.user, buyer=buyer)
            locked_board.purchase_rotation_index = (index + 1) % len(rotation)
            locked_board.save(update_fields=["purchase_rotation_index"])
        return Response(GroupPurchaseSerializer(purchase, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path=r"purchases/(?P<purchase_id>\d+)")
    def delete_purchase(self, request, pk=None, purchase_id=None):
        board = self.get_object()
        if not can_manage_board(request.user, board):
            return Response({"detail": "只有系统管理员或本组小组管理员可以删除采购记录。"}, status=status.HTTP_403_FORBIDDEN)
        purchase = get_object_or_404(GroupPurchase, pk=purchase_id, board=board)
        files = [purchase.payment_proof, purchase.invoice, purchase.item_image]
        purchase.delete()
        for file_field in files:
            if file_field:
                file_field.delete(save=False)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_purchase_for_buyer(self, request, board, purchase_id):
        purchase = get_object_or_404(GroupPurchase, pk=purchase_id, board=board)
        if purchase.buyer_id != request.user.id:
            return None, Response({"detail": "只有该采购单的采购人可以执行此操作。"}, status=status.HTTP_403_FORBIDDEN)
        return purchase, None

    @action(detail=True, methods=["post"], url_path=r"purchases/(?P<purchase_id>\d+)/pay")
    def pay_purchase(self, request, pk=None, purchase_id=None):
        purchase, error = self._get_purchase_for_buyer(request, self.get_object(), purchase_id)
        if error:
            return error
        if purchase.status != GroupPurchase.STATUS_ASSIGNED:
            return Response({"detail": "当前采购单不能重复登记支付。"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(request.data.get("payment_amount", "")))
            if amount <= 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            return Response({"payment_amount": ["请输入大于 0 的支付金额。"]}, status=status.HTTP_400_BAD_REQUEST)
        proof = request.FILES.get("payment_proof")
        if not proof:
            return Response({"payment_proof": ["请上传支付凭证。"]}, status=status.HTTP_400_BAD_REQUEST)
        purchase.payment_amount = amount
        purchase.payment_proof = proof
        purchase.paid_at = timezone.now()
        purchase.status = GroupPurchase.STATUS_PAID
        purchase.save()
        return Response(GroupPurchaseSerializer(purchase, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path=r"purchases/(?P<purchase_id>\d+)/arrive")
    def arrive_purchase(self, request, pk=None, purchase_id=None):
        purchase, error = self._get_purchase_for_buyer(request, self.get_object(), purchase_id)
        if error:
            return error
        if purchase.status != GroupPurchase.STATUS_PAID:
            return Response({"detail": "请先完成支付登记。"}, status=status.HTTP_400_BAD_REQUEST)
        invoice = request.FILES.get("invoice")
        item_image = request.FILES.get("item_image")
        errors = {}
        if not invoice:
            errors["invoice"] = ["请上传发票。"]
        if not item_image:
            errors["item_image"] = ["请上传实物图片。"]
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        purchase.invoice = invoice
        purchase.item_image = item_image
        purchase.arrived_at = timezone.now()
        purchase.status = GroupPurchase.STATUS_ARRIVED
        purchase.save()
        return Response(GroupPurchaseSerializer(purchase, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path=r"purchases/(?P<purchase_id>\d+)/reimburse")
    def reimburse_purchase(self, request, pk=None, purchase_id=None):
        purchase, error = self._get_purchase_for_buyer(request, self.get_object(), purchase_id)
        if error:
            return error
        if purchase.status != GroupPurchase.STATUS_ARRIVED:
            return Response({"detail": "请先上传发票和实物图片。"}, status=status.HTTP_400_BAD_REQUEST)
        purchase.status = GroupPurchase.STATUS_REIMBURSED
        purchase.reimbursed_at = timezone.now()
        purchase.save(update_fields=["status", "reimbursed_at", "updated_at"])
        return Response(GroupPurchaseSerializer(purchase, context={"request": request}).data)


class GroupAffairUnreadPopupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if is_land_host(user):
            return Response({"notices": [], "duty_reminder": None, "purchase_reminders": []})

        tutor = get_user_group_tutor(user)
        if not tutor:
            return Response({"notices": [], "duty_reminder": None, "purchase_reminders": []})

        board, _ = get_or_create_board_for_tutor(tutor)
        notices = (
            GroupAffairNotice.objects
            .filter(board=board)
            .exclude(read_records__user=user)
            .select_related("board", "board__tutor", "created_by")
            .order_by("created_at", "id")
        )
        duty_reminder = self._build_duty_reminder(board, user)
        purchase_reminders = self._build_purchase_reminders(board, user)
        return Response({
            "notices": GroupAffairNoticeSerializer(notices, many=True, context={"request": request}).data,
            "duty_reminder": duty_reminder,
            "purchase_reminders": purchase_reminders,
        })

    def _build_purchase_reminders(self, board, user):
        today = timezone.localdate()
        reminders = []
        purchases = board.purchases.filter(buyer=user).select_related("requester")
        for purchase in purchases:
            if purchase.status == GroupPurchase.STATUS_ASSIGNED:
                reminder_type = GroupPurchasePopupRead.TYPE_ASSIGNED
                reminder_date = purchase.created_at.date()
                title = "新的采购任务"
                content = f"{purchase.requester.name} 发起请购：{purchase.items}"
            elif purchase.status != GroupPurchase.STATUS_REIMBURSED and purchase.paid_at and purchase.paid_at <= timezone.now() - timedelta(days=7):
                reminder_type = GroupPurchasePopupRead.TYPE_REIMBURSEMENT
                reminder_date = today
                title = "采购报销逾期提醒"
                content = f"采购单 #{purchase.id} 支付已超过一周，请在报销完成后及时勾选已报销。"
            else:
                continue
            if GroupPurchasePopupRead.objects.filter(purchase=purchase, user=user, reminder_type=reminder_type, reminder_date=reminder_date).exists():
                continue
            reminders.append({"purchase_id": purchase.id, "type": reminder_type, "reminder_date": reminder_date.isoformat(), "title": title, "content": content})
        return reminders

    def _build_duty_reminder(self, board, user):
        if not board.duty_reminder_enabled:
            return None

        today = timezone.localdate()
        weekday = today.weekday()
        schedule = board.duty_schedule or []
        today_item = next(
            (
                item for item in schedule
                if isinstance(item, dict) and str(item.get("weekday")) == str(weekday)
            ),
            None,
        )
        if not today_item:
            return None

        try:
            duty_user_id = int(today_item.get("user_id")) if today_item.get("user_id") else None
        except (TypeError, ValueError):
            duty_user_id = None

        if duty_user_id != user.id:
            return None

        if GroupAffairDutyReminderRead.objects.filter(board=board, user=user, duty_date=today).exists():
            return None

        return {
            "board_id": board.id,
            "tutor_name": board.tutor.name,
            "duty_date": today.isoformat(),
            "weekday": weekday,
            "weekday_label": WEEKDAY_LABELS[weekday],
            "name": user.name,
        }


class GroupAffairDutyReminderReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        tutor = get_user_group_tutor(request.user)
        if not tutor:
            return Response({"detail": "当前用户没有所属小组。"}, status=status.HTTP_404_NOT_FOUND)

        board, _ = get_or_create_board_for_tutor(tutor)
        raw_date = request.data.get("duty_date")
        duty_date = parse_date(raw_date) if raw_date else timezone.localdate()
        if not duty_date:
            duty_date = timezone.localdate()

        read_record, _ = GroupAffairDutyReminderRead.objects.update_or_create(
            board=board,
            user=request.user,
            duty_date=duty_date,
            defaults={"read_at": timezone.now()},
        )
        return Response({"duty_date": duty_date.isoformat(), "read_at": read_record.read_at}, status=status.HTTP_200_OK)


class GroupPurchasePopupReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        purchase = get_object_or_404(GroupPurchase, pk=request.data.get("purchase_id"), buyer=request.user)
        reminder_type = request.data.get("type")
        if reminder_type not in dict(GroupPurchasePopupRead.TYPE_CHOICES):
            return Response({"type": ["无效的提醒类型。"]}, status=status.HTTP_400_BAD_REQUEST)
        reminder_date = parse_date(request.data.get("reminder_date", "")) or timezone.localdate()
        record, _ = GroupPurchasePopupRead.objects.update_or_create(
            purchase=purchase, user=request.user, reminder_type=reminder_type, reminder_date=reminder_date,
            defaults={"read_at": timezone.now()},
        )
        return Response({"read_at": record.read_at})
