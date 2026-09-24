# procurement/views/main/purchase_request_views.py
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from datetime import date
from decimal import Decimal, InvalidOperation
from django.db.models import Q
import json

from ...models import PurchaseRequest, RequestItem, Platform
from payment.models import Payment
from ...permissions import IsApprover, IsOwnerAndStatusEditable, IsOwnerAndPending
from common_serializers.serializers import PurchaseRequestSerializer, FullProcessPurchaseRequestSerializer
from ...filters import LedgerFilter


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# =============================================================================
# 1. 基类：包含所有共享逻辑
# =============================================================================
class BasePurchaseRequestViewSet(viewsets.ModelViewSet):
    """
    采购申请视图的基类，包含公共经费和公对公流程共享的逻辑。
    """
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = LedgerFilter
    search_fields = [
        'applicant__name', 'applicant__assigned_tutor__name', 'platform',
        'order_number', 'items__content', 'items__manufacturer', 'items__specifications',
        'handler__name'
    ]
    ordering_fields = ['total_price', 'request_date', 'order_number']

    queryset = PurchaseRequest.objects.filter(parent_request__isnull=True).order_by('-request_date')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return FullProcessPurchaseRequestSerializer
        return PurchaseRequestSerializer

    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'approve', 'reject', 'skip_inspection', 'skip_purchase_order',
                          'skip_contract',
                          'update_reimbursement_details', 'submit_purchase_links']:
            if self.action in ['approve', 'reject', 'skip_inspection', 'skip_purchase_order', 'skip_contract',
                               'update_reimbursement_details', 'submit_purchase_links']:
                self.permission_classes = [IsApprover]
            else:
                self.permission_classes = [IsOwnerAndStatusEditable]
        elif self.action == 'withdraw':
             self.permission_classes = [IsOwnerAndPending]
        else:
             self.permission_classes = [IsAuthenticated]  # Default permission

        return super().get_permissions()

    def get_requested_statuses(self):
        statuses = set()
        exact_status = self.request.query_params.get('status')
        status_in_str = self.request.query_params.get('status__in')
        if exact_status:
            if exact_status == 'pending_reimbursement':
                statuses.update(['accepted', 'inspection_skipped'])
            else:
                statuses.add(exact_status)
        if status_in_str:
            statuses.update([s.strip() for s in status_in_str.split(',')])
        return statuses

    def perform_create(self, serializer):
        purchase_request = serializer.save(applicant=self.request.user)
        for item in purchase_request.items.all():
            item.original_applicant = self.request.user
            item.save(update_fields=['original_applicant'])

    def perform_update(self, serializer):
        if serializer.instance.status == 'rejected':
            serializer.save(status='pending', rejection_reason=None)
        else:
            serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    def reject(self, request, pk=None):
        purchase_request = self.get_object()
        reason = request.data.get('reason', '未提供原因')
        purchase_request.status = 'rejected'
        purchase_request.rejection_reason = reason
        purchase_request.handler = None
        purchase_request.save(update_fields=['status', 'rejection_reason', 'handler'])
        return Response({'status': '申请已驳回'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerAndPending])
    def withdraw(self, request, pk=None):
        purchase_request = self.get_object()
        purchase_request.status = 'withdrawn'
        purchase_request.handler = None
        purchase_request.save(update_fields=['status', 'handler'])
        return Response({'status': '申请已撤回'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    def skip_inspection(self, request, pk=None):
        purchase_request = self.get_object()
        if purchase_request.status != 'invoiced':
            return Response(
                {'error': f"只有“待验收”状态的申请才能跳过验收。(当前状态: {purchase_request.get_status_display()})"},
                status=status.HTTP_400_BAD_REQUEST)
        purchase_request.status = 'inspection_skipped'
        purchase_request.save(update_fields=['status'])
        return Response({'status': '已跳过验收环节。'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='update-reimbursement-details', permission_classes=[IsApprover])
    @transaction.atomic
    def update_reimbursement_details(self, request, pk=None):
        # （保持与你原逻辑一致，此处略）
        from invoice.models import Invoice
        from inspection.models import Inspection
        from contract.models import Contract
        from purchase_order.models import PurchaseOrder

        parent_request = self.get_object()

        if parent_request.status not in ['accepted', 'inspection_skipped']:
            return Response(
                {'error': f'只有“待报销”状态的申请才能修改报销信息。当前状态: {parent_request.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST)

        total_price = request.data.get('total_price')
        if total_price not in (None, ''):
            try:
                parent_request.total_price = Decimal(total_price)
                parent_request.save(update_fields=['total_price'])
            except (InvalidOperation, TypeError):
                return Response({'error': '总金额格式不正确。'}, status=status.HTTP_400_BAD_REQUEST)

        po_form = request.FILES.get('po_form')
        if po_form and hasattr(parent_request, 'purchase_order'):
            po_instance, _ = PurchaseOrder.objects.get_or_create(purchase_request=parent_request)
            po_instance.po_form = po_form
            po_instance.save()

        contract_form = request.FILES.get('contract_form')
        if contract_form and hasattr(parent_request, 'contract'):
            contract_instance, _ = Contract.objects.get_or_create(purchase_request=parent_request)
            contract_instance.contract_form = contract_form
            contract_instance.save()

        inspection_photo = request.FILES.get('inspection_photo')
        inspection_number_raw = request.data.get('inspection_number')
        inspection_number = None
        if inspection_number_raw is not None:
            inspection_number = str(inspection_number_raw).strip()
        has_inspection_number = bool(inspection_number)
        if inspection_photo or has_inspection_number:
            inspection = getattr(parent_request, 'inspection', None)
            if inspection:
                if inspection_photo:
                    inspection.inspection_photo = inspection_photo
                if has_inspection_number:
                    inspection.inspection_number = inspection_number
                inspection.save()
            else:
                if not inspection_photo or not has_inspection_number:
                    return Response(
                        {'error': '缺少完整验收信息，无法新建验收。'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                Inspection.objects.create(
                    purchase_request=parent_request,
                    inspection_number=inspection_number,
                    inspection_photo=inspection_photo,
                    inspector=request.user
                )

        if not parent_request.merged_children.exists():
            payment_photo = request.FILES.get('payment_photo')
            if payment_photo:
                payment, created = Payment.objects.get_or_create(
                    purchase_request=parent_request,
                    defaults={'paid_by': request.user, 'payment_photo': payment_photo}
                )
                if not created:
                    payment.payment_photo = payment_photo
                    if payment.paid_by_id is None:
                        payment.paid_by = request.user
                    payment.save()

            invoice_image = request.FILES.get('invoice_image')
            invoice_number = request.data.get('invoice_number')
            invoice_company = request.data.get('invoice_company')
            if invoice_image or (invoice_number is not None) or (invoice_company is not None):
                invoice = parent_request.invoices.order_by('-created_at').first()
                if not invoice:
                    if invoice_number is None or invoice_company is None or not invoice_image:
                        return Response({'error': '缺少完整发票信息，无法新建发票。'}, status=status.HTTP_400_BAD_REQUEST)
                    invoice = Invoice.objects.create(
                        purchase_request=parent_request,
                        submitted_by=request.user,
                        invoice_number=invoice_number,
                        company_name=invoice_company,
                        invoice_image=invoice_image,
                    )
                    invoice_image = None
                if invoice_image:
                    invoice.invoice_image = invoice_image
                if invoice_number is not None:
                    invoice.invoice_number = invoice_number
                if invoice_company is not None:
                    invoice.company_name = invoice_company
                invoice.save()

        children_updates_str = request.data.get('children_updates')
        if children_updates_str:
            try:
                children_data = json.loads(children_updates_str)
                for child_data in children_data:
                    child_id = child_data.get('id')
                    if not child_id:
                        continue

                    try:
                        child_req = PurchaseRequest.objects.get(pk=child_id, parent_request=parent_request)
                    except PurchaseRequest.DoesNotExist:
                        continue
                    child_total_price = child_data.get('total_price')
                    if child_total_price not in (None, ''):
                        try:
                            child_req.total_price = Decimal(child_total_price)
                            child_req.save(update_fields=['total_price'])
                        except (InvalidOperation, TypeError):
                            return Response({'error': f'子申请 {child_id} 的总金额格式不正确。'},
                                            status=status.HTTP_400_BAD_REQUEST)

                    child_payment_photo = request.FILES.get(f'child_{child_id}_payment_photo')
                    if child_payment_photo:
                        payment, created = Payment.objects.get_or_create(
                            purchase_request=child_req,
                            defaults={'paid_by': child_req.applicant, 'payment_photo': child_payment_photo}
                        )
                        if not created:
                            payment.payment_photo = child_payment_photo
                            if payment.paid_by_id is None:
                                payment.paid_by = child_req.applicant
                            payment.save()

                    child_invoice_number = child_data.get('invoice_number')
                    child_invoice_company = child_data.get('invoice_company')
                    child_invoice_image = request.FILES.get(f'child_{child_id}_invoice_image')

                    if (child_invoice_image or (child_invoice_number is not None) or (
                            child_invoice_company is not None)):
                        invoice = child_req.invoices.order_by('-created_at').first()
                        if not invoice:
                            if child_invoice_number is None or child_invoice_company is None or not child_invoice_image:
                                return Response({'error': f'子申请 {child_id} 发票信息不完整，无法新建发票。'},
                                                status=status.HTTP_400_BAD_REQUEST)
                            invoice = Invoice.objects.create(
                                purchase_request=child_req,
                                submitted_by=request.user,
                                invoice_number=child_invoice_number,
                                company_name=child_invoice_company,
                                invoice_image=child_invoice_image,
                            )
                            child_invoice_image = None
                        if child_invoice_image:
                            invoice.invoice_image = child_invoice_image
                        if child_invoice_number is not None:
                            invoice.invoice_number = child_invoice_number
                        if child_invoice_company is not None:
                            invoice.company_name = child_invoice_company
                        invoice.save()

            except json.JSONDecodeError:
                return Response({'error': 'children_updates 格式无效。'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'error': f'处理子申请更新时出错: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'status': '报销相关信息已成功更新。'}, status=status.HTTP_200_OK)


# =============================================================================
# 2. 公共经费子类
# =============================================================================
class PublicPurchaseRequestViewSet(BasePurchaseRequestViewSet):
    """
    专门处理公共经费（Public）采购流程的视图集。
    """

    def get_queryset(self):
        user = self.request.user
        base_queryset = self.queryset.filter(expense_type='public')

        prefetch_relations = ['items', 'merged_children', 'merged_children__handler', 'invoices', 'merged_children__invoices', 'merged_children__reimbursement_details']
        select_related_relations = ['applicant', 'approved_by', 'applicant__assigned_tutor', 'handler', 'reimbursement_details']

        if self.action == 'retrieve':
            prefetch_relations.extend(['merged_children__items', 'merged_children__applicant'])
            return base_queryset.select_related(*select_related_relations).prefetch_related(*prefetch_relations)

        if self.action != 'list':
            return base_queryset.select_related(*select_related_relations).prefetch_related(*prefetch_relations)

        scope = self.request.query_params.get('scope', 'mine')
        if scope == 'mine':
            queryset = base_queryset.filter(Q(applicant=user) | Q(merged_children__applicant=user))
        else:  # scope == 'all'
            user_roles = set(user.roles.values_list('name', flat=True))
            is_admin = '系统管理员' in user_roles
            is_tutor = '导师用户' in user_roles

            if is_admin or is_tutor:
                queryset = base_queryset  # Admins and Tutors see everything
            else:
                is_procurement_staff = '采购人员' in user_roles
                if is_procurement_staff:
                    requested_statuses = self.get_requested_statuses()
                    handled_statuses = {'paid', 'goods_received', 'invoiced', 'accepted', 'inspection_skipped', 'reimbursed', 'completed'}

                    # --- START OF FINAL MODIFICATION --- (Logic for Overview tab)
                    if not requested_statuses:  # This is the Overview tab case
                        queryset = base_queryset  # Procurement staff see all in Overview
                    # --- END OF FINAL MODIFICATION ---
                    elif requested_statuses.issubset({'pending', 'payment_rejected'}):
                        queryset = base_queryset.filter(status__in=list(requested_statuses))
                    elif any(s in handled_statuses for s in requested_statuses):
                        queryset = base_queryset.filter(status__in=list(requested_statuses)).filter(
                            Q(handler=user) | Q(handler__isnull=True, merged_children__handler=user)
                        )
                    else:
                        # Fallback: Show pending/rejected OR handled by user if specific non-handled status requested
                        queryset = base_queryset.filter(
                            Q(status__in=list(requested_statuses)) & (
                                Q(status__in=['pending', 'payment_rejected'])
                                | Q(handler=user)
                                | Q(handler__isnull=True, merged_children__handler=user)
                            )
                        )
                else:
                    queryset = base_queryset.none()

        # Apply status filters AFTER visibility is determined
        # Only needed for 'mine' scope or admin/tutor 'all' scope now, as staff logic incorporates status filtering
        if scope == 'mine' or (scope == 'all' and (is_admin or is_tutor)):
             requested_statuses = self.get_requested_statuses()
             if requested_statuses:
                 queryset = queryset.filter(status__in=list(requested_statuses))

        return queryset.select_related(*select_related_relations).prefetch_related(*prefetch_relations).distinct()

    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    @transaction.atomic
    def approve(self, request, pk=None):
        purchase_request = self.get_object()

        if purchase_request.status in ('pending', 'payment_rejected'):
            # 校验平台与前缀
            try:
                platform_obj = Platform.objects.get(name=purchase_request.platform)
                if not platform_obj.prefix:
                    return Response({'error': f'平台“{platform_obj.name}”未设置单号前缀，请前往平台管理页面进行设置。'},
                                    status=status.HTTP_400_BAD_REQUEST)
                prefix = platform_obj.prefix
            except Platform.DoesNotExist:
                return Response({'error': f'未在平台列表中找到“{purchase_request.platform}”，请先在平台管理中添加。'},
                                status=status.HTTP_400_BAD_REQUEST)

            today = date.today()

            # 必须上传支付截图
            payment_photo = request.FILES.get('payment_photo')
            if not payment_photo:
                return Response({'error': '批准公共经费申请时必须上传支付截图。'}, status=status.HTTP_400_BAD_REQUEST)

            # 幂等：已有单号则不再生成
            if not purchase_request.order_number:
                # 冲突重试
                for _ in range(3):
                    try:
                        # 生成唯一单号（在本事务内行级锁保护）
                        new_order_number = PurchaseRequest.generate_order_number_atomic(
                            platform=purchase_request.platform,
                            prefix=prefix,
                            the_date=today
                        )
                        purchase_request.order_number = new_order_number
                        purchase_request.approval_date = today
                        purchase_request.save(update_fields=['order_number', 'approval_date'])
                        break
                    except IntegrityError:
                        # 冲突时重试
                        transaction.set_rollback(False)
                        continue
                else:
                    return Response({'error': '生成单号时发生并发冲突，请稍后重试。'}, status=status.HTTP_409_CONFLICT)
            else:
                # 已有单号则补充批准日期
                if not purchase_request.approval_date:
                    purchase_request.approval_date = today
                    purchase_request.save(update_fields=['approval_date'])

            # 创建支付记录并流转状态
            Payment.objects.create(purchase_request=purchase_request, payment_photo=payment_photo, paid_by=request.user)
            purchase_request.status = 'paid'
            purchase_request.approved_by = request.user
            purchase_request.rejection_reason = None
            purchase_request.handler = request.user
            purchase_request.save(update_fields=['status', 'approved_by', 'rejection_reason', 'handler'])

            return Response({'status': f'申请已批准，新单号为 {purchase_request.order_number}。'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': f'只有“待审批”或“付款被驳回”状态的申请才能被批准。(当前状态: {purchase_request.get_status_display()})'},
                            status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# 3. 公对公子类
# =============================================================================
class C2CPurchaseRequestViewSet(BasePurchaseRequestViewSet):
    """
    专门处理公对公（C2C）采购流程的视图集。
    """

    def get_queryset(self):
        user = self.request.user
        base_queryset = self.queryset.filter(expense_type='c2c')

        prefetch_relations = ['items', 'merged_children__items', 'merged_children__applicant', 'merged_children__handler', 'invoices', 'merged_children__invoices', 'merged_children__reimbursement_details']
        select_related_relations = ['applicant', 'approved_by', 'applicant__assigned_tutor', 'handler', 'reimbursement_details']

        if self.action == 'retrieve':
            prefetch_relations.extend([
                'merged_children__purchase_order', 'merged_children__contract', 'merged_children__acceptance',
                'merged_children__payment', 'merged_children__invoices', 'merged_children__inspection'
            ])
            select_related_relations.extend([
                 'purchase_order', 'contract', 'acceptance', 'payment', 'inspection'
            ])
            return base_queryset.select_related(*select_related_relations).prefetch_related(*prefetch_relations)

        if self.action != 'list':
            return base_queryset.select_related(*select_related_relations).prefetch_related(*prefetch_relations)

        scope = self.request.query_params.get('scope', 'mine')
        if scope == 'mine':
            queryset = base_queryset.filter(Q(applicant=user) | Q(merged_children__applicant=user))
        else:  # scope == 'all'
            user_roles = set(user.roles.values_list('name', flat=True))
            is_admin = '系统管理员' in user_roles
            is_tutor = '导师用户' in user_roles

            if is_admin or is_tutor:
                queryset = base_queryset
            else:
                managed_c2c_platforms = Platform.objects.filter(managers=user, category='c2c').values_list('name',
                                                                                                          flat=True)
                if managed_c2c_platforms:
                    queryset = base_queryset.filter(platform__in=list(managed_c2c_platforms))
                else:
                    queryset = base_queryset.none()

        requested_statuses = self.get_requested_statuses()
        if requested_statuses:
            queryset = queryset.filter(status__in=list(requested_statuses))

        return queryset.select_related(*select_related_relations).prefetch_related(*prefetch_relations).distinct()

    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    @transaction.atomic
    def approve(self, request, pk=None):
        purchase_request = self.get_object()

        if purchase_request.status in ('pending', 'payment_rejected'):
            # 校验平台与前缀
            try:
                platform_obj = Platform.objects.get(name=purchase_request.platform)
                if not platform_obj.prefix:
                    return Response({'error': f'平台“{platform_obj.name}”未设置单号前缀，请前往平台管理页面进行设置。'},
                                    status=status.HTTP_400_BAD_REQUEST)
                prefix = platform_obj.prefix
            except Platform.DoesNotExist:
                return Response({'error': f'未在平台列表中找到“{purchase_request.platform}”，请先在平台管理中添加。'},
                                status=status.HTTP_400_BAD_REQUEST)

            today = date.today()

            # 幂等：已有单号则不再生成
            if not purchase_request.order_number:
                for _ in range(3):
                    try:
                        new_order_number = PurchaseRequest.generate_order_number_atomic(
                            platform=purchase_request.platform,
                            prefix=prefix,
                            the_date=today
                        )
                        purchase_request.order_number = new_order_number
                        purchase_request.approval_date = today
                        purchase_request.save(update_fields=['order_number', 'approval_date'])
                        break
                    except IntegrityError:
                        transaction.set_rollback(False)
                        continue
                else:
                    return Response({'error': '生成单号时发生并发冲突，请稍后重试。'}, status=status.HTTP_409_CONFLICT)
            else:
                if not purchase_request.approval_date:
                    purchase_request.approval_date = today
                    purchase_request.save(update_fields=['approval_date'])

            purchase_request.status = 'pending_purchase_order'
            purchase_request.approved_by = request.user
            purchase_request.rejection_reason = None
            purchase_request.handler = request.user
            purchase_request.save(update_fields=['status', 'approved_by', 'rejection_reason', 'handler'])
            return Response({'status': f'申请已批准，新单号为 {purchase_request.order_number}。'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': f'只有“待审批”或“付款被驳回”状态的申请才能被批准。(当前状态: {purchase_request.get_status_display()})'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='submit-links', permission_classes=[IsApprover])
    @transaction.atomic
    def submit_purchase_links(self, request, pk=None):
        # （保持原逻辑不变）
        purchase_request = self.get_object()
        if purchase_request.status != 'pending_purchase_order':
            return Response(
                {'error': f'只有“待请购”状态的申请才能提交链接。当前状态: {purchase_request.get_status_display()}'},
                status=status.HTTP_400_BAD_REQUEST)

        items_data = request.data.get('links', [])
        if not isinstance(items_data, list):
            return Response({'error': '链接数据格式不正确，应为列表。'}, status=status.HTTP_400_BAD_REQUEST)

        if len(items_data) != purchase_request.items.count():
            return Response({'error': '提交的链接数量与申请中的物品数量不匹配。'}, status=status.HTTP_400_BAD_REQUEST)

        for item_data in items_data:
            link = item_data.get('link')
            if not link or not isinstance(link, str) or not link.strip():
                try:
                    item_name = RequestItem.objects.get(id=item_data.get('item_id')).content
                    return Response({'error': f'物品 "{item_name}" 的采购链接不能为空。'},
                                    status=status.HTTP_400_BAD_REQUEST)
                except RequestItem.DoesNotExist:
                    return Response({'error': f"ID为 {item_data.get('item_id')} 的物品不存在。"},
                                    status=status.HTTP_400_BAD_REQUEST)

        for item_data in items_data:
            item_id = item_data.get('item_id')
            link = item_data.get('link')
            RequestItem.objects.filter(id=item_id, purchase_request=purchase_request).update(purchase_link=link.strip())

        purchase_request.status = 'pending_contract'
        purchase_request.save(update_fields=['status'])
        return Response({'status': '采购链接已提交，申请已进入“待合同”阶段。'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    def skip_purchase_order(self, request, pk=None):
        purchase_request = self.get_object()
        if purchase_request.status != 'pending_purchase_order':
            return Response({'error': '只有“待请购”状态的申请才能跳过此环节。'}, status=status.HTTP_400_BAD_REQUEST)
        purchase_request.status = 'pending_contract'
        purchase_request.save(update_fields=['status'])
        return Response({'status': '已跳过请购单环节。'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsApprover])
    def skip_contract(self, request, pk=None):
        purchase_request = self.get_object()
        if purchase_request.status != 'pending_contract':
            return Response({'error': '只有“待合同”状态的申请才能跳过此环节。'}, status=status.HTTP_400_BAD_REQUEST)
        purchase_request.status = 'paid'
        purchase_request.save(update_fields=['status'])
        return Response({'status': '已跳过合同环节。'}, status=status.HTTP_200_OK)
