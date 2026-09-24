from django.contrib import admin
from .models import PublicExpenseRecord, C2CExpenseRecord

@admin.register(PublicExpenseRecord)
class PublicExpenseRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'applicant_name', 'platform', 'content', 'total_price', 'tutor_name')
    list_filter = ('platform', 'date', 'tutor_name')
    search_fields = ('applicant_name', 'content', 'order_number')

@admin.register(C2CExpenseRecord)
class C2CExpenseRecordAdmin(admin.ModelAdmin):
    # 您可以根据需要自定义C2C表的显示
    list_display = ('date', 'platform', 'order_number')