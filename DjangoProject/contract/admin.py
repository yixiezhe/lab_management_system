# DjangoProject/contract/admin.py

from django.contrib import admin
from .models import Contract

@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ('id', 'purchase_request', 'uploaded_by', 'uploaded_at')
    search_fields = ('purchase_request__order_number',)