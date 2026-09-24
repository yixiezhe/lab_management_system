from django.contrib import admin
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.utils.html import format_html
from django import forms
import pandas as pd
from .models import AnnouncementRead, PurchaseRequest, RequestItem, WhitelistItem, GlobalAnnouncement


# --- 表单定义 ---
class ExcelImportForm(forms.Form):
    excel_file = forms.FileField(label="选择Excel文件 (.xlsx)")


# --- PurchaseRequest Admin (将内联类定义放在前面) ---
class RequestItemInline(admin.TabularInline):
    model = RequestItem
    fk_name = 'purchase_request'
    extra = 0
    readonly_fields = ('purchase_type', 'content', 'manufacturer', 'parameters', 'specifications', 'unit_price',
                       'quantity', 'purchase_link')
    can_delete = False


@admin.register(PurchaseRequest)
class PurchaseRequestAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'request_date', 'status', 'expense_type', 'platform', 'total_price')
    list_filter = ('status', 'request_date', 'expense_type', 'platform')
    search_fields = ('applicant__name', 'items__content')
    inlines = [RequestItemInline]


@admin.register(WhitelistItem)
class WhitelistItemAdmin(admin.ModelAdmin):
    list_display = ('content', 'main_category', 'platform', 'purchase_type', 'manufacturer', 'specifications')
    list_filter = ('main_category', 'platform', 'purchase_type')
    search_fields = ('content', 'manufacturer', 'cas_number', 'product_number')
    change_list_template = "admin/whitelist_changelist.html"

    def get_urls(self):
        urls = super().get_urls()
        info = self.model._meta.app_label, self.model._meta.model_name
        custom_urls = [
            path(
                'import-excel/',
                self.admin_site.admin_view(self.import_excel_view),
                name=f'{info[0]}_{info[1]}_import_excel'
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        info = self.model._meta.app_label, self.model._meta.model_name
        extra_context['import_url'] = reverse(f'admin:{info[0]}_{info[1]}_import_excel')
        return super().changelist_view(request, extra_context=extra_context)

    def import_excel_view(self, request):
        if request.method == "POST":
            form = ExcelImportForm(request.POST, request.FILES)
            if not form.is_valid():
                self.message_user(request, "操作失败：请选择一个有效的Excel文件。", level='error')
                return redirect(".")
            excel_file = request.FILES["excel_file"]
            try:
                df = pd.read_excel(excel_file).fillna('')
                df.columns = df.columns.str.strip()
                column_mapping = {
                    '主分类': 'main_category', '平台/服务': 'platform', '采购类型': 'purchase_type',
                    '采购内容': 'content', '厂商': 'manufacturer', 'CAS号': 'cas_number',
                    '货号': 'product_number', '参数': 'parameters', '规格': 'specifications',
                }
                required_columns = ['主分类', '平台/服务', '采购类型', '采购内容']
                if not all(col in df.columns for col in required_columns):
                    missing = ", ".join(set(col for col in required_columns if col not in df.columns))
                    raise ValueError(f"Excel文件中缺少以下必需的列: {missing}")
                category_mapping = {
                    '公对公': 'c2c', '公共经费': 'public', '耗材': 'consumable',
                    '药品': 'chemical', '设备': 'equipment', '其他': 'other',
                }
                created_count, updated_count = 0, 0
                for index, row in df.iterrows():
                    try:
                        content = str(row.get('采购内容', '')).strip()
                        if not content or content.lower() == 'nan': continue
                        data = {model_field: str(row.get(excel_col, '')).strip() for excel_col, model_field in
                                column_mapping.items()}
                        data['main_category'] = category_mapping.get(data['main_category'])
                        data['purchase_type'] = category_mapping.get(data['purchase_type'])
                        obj, created = WhitelistItem.objects.update_or_create(content=content, defaults=data)
                        if created:
                            created_count += 1
                        else:
                            updated_count += 1
                    except Exception as row_error:
                        self.message_user(request, f"处理Excel第 {index + 2} 行失败：{row_error}", level='warning')
                self.message_user(request, f"导入成功！新增 {created_count} 条，更新 {updated_count} 条。")
            except Exception as e:
                self.message_user(request, f"导入失败：{e}", level='error')

            list_url = reverse('admin:procurement_whitelistitem_changelist')
            return redirect(list_url)

        form = ExcelImportForm()
        context = self.admin_site.each_context(request)
        context['title'] = "从Excel导入白名单"
        context['form'] = form
        return render(request, "admin/excel_import.html", context)


# --- START OF MODIFICATION ---
@admin.register(GlobalAnnouncement)
class GlobalAnnouncementAdmin(admin.ModelAdmin):
    """
    公告后台管理界面。
    """
    list_display = ('title', 'is_published', 'show_popup', 'created_at', 'updated_at', 'updated_by')
    list_filter = ('is_published', 'show_popup', 'created_at', 'updated_at')
    search_fields = ('title', 'content')
    readonly_fields = ('created_at', 'updated_at', 'created_by', 'updated_by')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
# --- END OF MODIFICATION ---


@admin.register(AnnouncementRead)
class AnnouncementReadAdmin(admin.ModelAdmin):
    list_display = ('announcement', 'user', 'read_at')
    list_filter = ('read_at',)
    search_fields = ('announcement__title', 'user__name', 'user__username')
    readonly_fields = ('announcement', 'user', 'read_at')
