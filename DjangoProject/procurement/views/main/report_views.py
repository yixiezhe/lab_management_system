from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import PurchaseRequest


SPENT_STATUSES = (
    'paid',
    'goods_received',
    'invoiced',
    'accepted',
    'inspection_skipped',
    'reimbursed',
    'completed',
)


class IsPublicExpenseReportAdmin(BasePermission):
    """Only system administrators can read public expense reports."""

    message = '只有系统管理员可以查看公共经费报表。'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, 'is_system_admin', False):
            return True
        return user.roles.filter(name='系统管理员').exists()


class PublicExpenseReportView(APIView):
    """
    Administrator-only read model for public procurement spending.

    Spending is counted after a public request has entered the paid-and-later
    workflow. Merged parent requests are excluded to avoid double counting;
    their merged child requests keep the original applicant/tutor attribution.
    """

    permission_classes = [IsPublicExpenseReportAdmin]

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        selected_year = self._parse_year(request.query_params.get('year'), today.year)
        records = list(self._get_expense_records())
        available_years = sorted({self._expense_date(record).year for record in records}, reverse=True)
        if selected_year not in available_years and available_years:
            selected_year = available_years[0]

        year_records = [record for record in records if self._expense_date(record).year == selected_year]
        filters = self._parse_filters(request.query_params)
        filtered_records = self._apply_filters(year_records, filters)

        overall_total = sum(((record.total_price or Decimal('0')) for record in records), Decimal('0'))
        selected_total = sum(((record.total_price or Decimal('0')) for record in filtered_records), Decimal('0'))
        current_month_total = sum(
            (record.total_price or Decimal('0'))
            for record in self._apply_filters(records, {
                'month': today.month,
                'applicant_id': filters['applicant_id'],
                'tutor_id': filters['tutor_id'],
            })
            if self._expense_date(record).year == today.year
        )

        monthly = self._build_monthly_rows(filtered_records, selected_year)
        people = self._build_person_rows(filtered_records)
        tutors = self._build_tutor_rows(filtered_records)

        return Response({
            'year': selected_year,
            'available_years': available_years or [selected_year],
            'spending_statuses': list(SPENT_STATUSES),
            'filters': filters,
            'filter_options': self._build_filter_options(year_records),
            'summary': {
                'overall_total_amount': self._money(overall_total),
                'selected_year_total_amount': self._money(selected_total),
                'selected_year_request_count': len(filtered_records),
                'current_month_total_amount': self._money(current_month_total),
                'person_count': len(people),
                'tutor_count': len(tutors),
            },
            'monthly': monthly,
            'people': people,
            'tutors': tutors,
        })

    def _get_expense_records(self):
        parent_ids_with_children = PurchaseRequest.objects.filter(
            expense_type='public',
            merged_children__isnull=False,
        ).values('id')

        return (
            PurchaseRequest.objects
            .filter(expense_type='public')
            .filter(
                Q(parent_request__isnull=True, status__in=SPENT_STATUSES) |
                Q(parent_request__isnull=False, status='merged', merged_from_status__in=SPENT_STATUSES)
            )
            .exclude(id__in=parent_ids_with_children)
            .select_related('applicant', 'applicant_tutor', 'applicant__assigned_tutor')
            .order_by('approval_date', 'request_date', 'id')
        )

    @staticmethod
    def _expense_date(record):
        return record.approval_date or record.request_date

    @staticmethod
    def _parse_year(raw_year, default_year):
        try:
            year = int(raw_year)
        except (TypeError, ValueError):
            return default_year
        if year < 2000 or year > 2100:
            return default_year
        return year

    def _parse_filters(self, query_params):
        return {
            'month': self._parse_int(query_params.get('month'), 1, 12),
            'applicant_id': self._parse_int(query_params.get('applicant_id'), 0, None),
            'tutor_id': self._parse_int(query_params.get('tutor_id'), 0, None),
        }

    @staticmethod
    def _parse_int(raw_value, minimum=None, maximum=None):
        if raw_value in (None, ''):
            return None
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            return None
        if minimum is not None and value < minimum:
            return None
        if maximum is not None and value > maximum:
            return None
        return value

    def _apply_filters(self, records, filters):
        filtered = []
        for record in records:
            expense_date = self._expense_date(record)
            applicant = record.applicant
            tutor = record.applicant_tutor or getattr(applicant, 'assigned_tutor', None)
            tutor_id = getattr(tutor, 'id', None) or 0

            if filters.get('month') and expense_date.month != filters['month']:
                continue
            if filters.get('applicant_id') is not None and getattr(applicant, 'id', None) != filters['applicant_id']:
                continue
            if filters.get('tutor_id') is not None and tutor_id != filters['tutor_id']:
                continue
            filtered.append(record)
        return filtered

    @staticmethod
    def _money(value):
        return str((value or Decimal('0')).quantize(Decimal('0.01')))

    def _build_filter_options(self, records):
        applicant_map = {}
        tutor_map = {}

        for record in records:
            applicant = record.applicant
            tutor = record.applicant_tutor or getattr(applicant, 'assigned_tutor', None)
            applicant_id = getattr(applicant, 'id', None)
            tutor_id = getattr(tutor, 'id', None) or 0

            if applicant_id is not None:
                applicant_map[applicant_id] = getattr(applicant, 'name', '未知用户')
            tutor_map[tutor_id] = getattr(tutor, 'name', None) or '未分配导师'

        return {
            'months': [{'value': month, 'label': f'{month}月'} for month in range(1, 13)],
            'applicants': [
                {'id': applicant_id, 'name': name}
                for applicant_id, name in sorted(applicant_map.items(), key=lambda item: item[1])
            ],
            'tutors': [
                {'id': tutor_id, 'name': name}
                for tutor_id, name in sorted(tutor_map.items(), key=lambda item: item[1])
            ],
        }

    def _build_monthly_rows(self, records, year):
        month_map = {
            month: {'amount': Decimal('0'), 'count': 0}
            for month in range(1, 13)
        }
        for record in records:
            expense_date = self._expense_date(record)
            month_map[expense_date.month]['amount'] += record.total_price or Decimal('0')
            month_map[expense_date.month]['count'] += 1

        return [
            {
                'month': f'{year}-{month:02d}',
                'label': f'{month}月',
                'amount': self._money(data['amount']),
                'count': data['count'],
            }
            for month, data in month_map.items()
        ]

    def _build_person_rows(self, records):
        grouped = {}
        for record in records:
            applicant = record.applicant
            tutor = record.applicant_tutor or getattr(applicant, 'assigned_tutor', None)
            applicant_id = getattr(applicant, 'id', None) or 0
            row = grouped.setdefault(applicant_id, {
                'applicant_id': applicant_id,
                'applicant_name': getattr(applicant, 'name', '未知用户'),
                'tutor_id': getattr(tutor, 'id', None),
                'tutor_name': getattr(tutor, 'name', None) or '未分配导师',
                'amount_value': Decimal('0'),
                'request_count': 0,
            })
            row['amount_value'] += record.total_price or Decimal('0')
            row['request_count'] += 1

        rows = sorted(grouped.values(), key=lambda item: item['amount_value'], reverse=True)
        return [
            {
                'rank': index,
                'applicant_id': row['applicant_id'],
                'applicant_name': row['applicant_name'],
                'tutor_id': row['tutor_id'],
                'tutor_name': row['tutor_name'],
                'total_amount': self._money(row['amount_value']),
                'request_count': row['request_count'],
            }
            for index, row in enumerate(rows, start=1)
        ]

    def _build_tutor_rows(self, records):
        grouped = {}
        for record in records:
            applicant = record.applicant
            tutor = record.applicant_tutor or getattr(applicant, 'assigned_tutor', None)
            tutor_id = getattr(tutor, 'id', None) or 0
            row = grouped.setdefault(tutor_id, {
                'tutor_id': getattr(tutor, 'id', None),
                'tutor_name': getattr(tutor, 'name', None) or '未分配导师',
                'amount_value': Decimal('0'),
                'student_ids': set(),
                'request_count': 0,
            })
            row['amount_value'] += record.total_price or Decimal('0')
            row['student_ids'].add(getattr(applicant, 'id', None))
            row['request_count'] += 1

        rows = sorted(grouped.values(), key=lambda item: item['amount_value'], reverse=True)
        return [
            {
                'rank': index,
                'tutor_id': row['tutor_id'],
                'tutor_name': row['tutor_name'],
                'total_amount': self._money(row['amount_value']),
                'student_count': len([student_id for student_id in row['student_ids'] if student_id is not None]),
                'request_count': row['request_count'],
            }
            for index, row in enumerate(rows, start=1)
        ]
