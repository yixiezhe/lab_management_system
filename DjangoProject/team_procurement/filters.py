# team_procurement/filters.py

import django_filters
from .models import TeamPurchaseRequest
from users.models import UserProfile


class TeamLedgerFilter(django_filters.FilterSet):
    """
    为小组采购台账定义的筛选器类。
    """
    # 1. 日期范围筛选
    request_date = django_filters.DateFromToRangeFilter(
        field_name='request_date',
        label='申请日期范围'
    )

    # 2. 申请人筛选
    applicant = django_filters.ModelChoiceFilter(
        field_name='applicant',
        queryset=UserProfile.objects.all(),
        label='申请人'
    )

    # 3. 导师筛选
    tutor = django_filters.ModelChoiceFilter(
        field_name='tutor',
        queryset=UserProfile.objects.filter(roles__name='导师用户'),
        label='导师'
    )

    class Meta:
        model = TeamPurchaseRequest
        fields = ['request_date', 'applicant', 'tutor']