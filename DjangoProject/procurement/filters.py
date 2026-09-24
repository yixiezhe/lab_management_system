import django_filters
from django.db.models import Q
from .models import PurchaseRequest
from users.models import UserProfile


class LedgerFilter(django_filters.FilterSet):
    """
    为公共采购台账定义的筛选器类。
    """
    request_date = django_filters.DateFromToRangeFilter(
        field_name='request_date',
        label='申请日期范围'
    )
    applicant = django_filters.ModelChoiceFilter(
        field_name='applicant',
        queryset=UserProfile.objects.all(),
        label='申请人'
    )
    handler = django_filters.ModelChoiceFilter(
        field_name='handler',
        queryset=UserProfile.objects.all(),
        label='采购人'
    )
    tutor = django_filters.ModelChoiceFilter(
        field_name='applicant__assigned_tutor',
        queryset=UserProfile.objects.filter(roles__name='导师用户'),
        label='导师'
    )
    is_paid = django_filters.BooleanFilter(
        method='filter_is_paid',
        label='是否已支付 (True/False)'
    )
    is_invoiced = django_filters.BooleanFilter(
        method='filter_is_invoiced',
        label='是否已报销 (True/False)'
    )
    is_accepted = django_filters.BooleanFilter(
        method='filter_is_accepted',
        label='是否已验收 (True/False)'
    )

    requires_inspection = django_filters.BooleanFilter(
        method='filter_requires_inspection',
        label='是否需要验收'
    )
    invoice_number = django_filters.CharFilter(
        method='filter_invoice_number',
        label='发票单号'
    )
    platform = django_filters.CharFilter(
        field_name='platform',
        lookup_expr='exact',
        label='平台'
    )

    class Meta:
        model = PurchaseRequest
        fields = ['request_date', 'applicant', 'handler', 'tutor', 'platform', 'requires_inspection', 'invoice_number']

    def filter_is_paid(self, queryset, name, value):
        lookup = 'payment__isnull'
        return queryset.filter(**{lookup: not value})

    def filter_is_invoiced(self, queryset, name, value):
        lookup = 'invoices__isnull'
        return queryset.filter(**{lookup: not value}).distinct()

    def filter_is_accepted(self, queryset, name, value):
        lookup = 'acceptance__isnull'
        return queryset.filter(**{lookup: not value})

    # --- 【核心修改】修正筛选逻辑，使其作用于正确的 status 字段 ---
    def filter_requires_inspection(self, queryset, name, value):
        """
        根据 PurchaseRequest 的最终状态 (status) 进行筛选。
        'value' == True  (需要验收) -> 筛选出 status = 'accepted' 的记录
        'value' == False (无需验收) -> 筛选出 status = 'inspection_skipped' 的记录
        """
        if value is True:
            return queryset.filter(status='accepted')
        elif value is False:
            return queryset.filter(status='inspection_skipped')

        # 如果 value 不是 True 或 False (例如用户选择“全部”)，则不应用此筛选
        return queryset

    def filter_invoice_number(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(invoices__invoice_number__icontains=value)
            | Q(merged_children__invoices__invoice_number__icontains=value)
        ).distinct()
