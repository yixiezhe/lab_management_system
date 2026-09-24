# expense_report/serializers.py
from rest_framework import serializers
from .models import ExpenseReport

class ExpenseReportSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(source='submitted_by.name', read_only=True)

    class Meta:
        model = ExpenseReport
        fields = '__all__'
        read_only_fields = ('submitted_by',)