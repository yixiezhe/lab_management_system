from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("procurement", "0018_purchaserequest_handler"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaserequest",
            name="merged_from_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("pending", "待审批"),
                    ("rejected", "已驳回"),
                    ("withdrawn", "已撤回"),
                    ("payment_rejected", "付款已驳回"),
                    ("pending_purchase_order", "待请购"),
                    ("pending_contract", "待合同"),
                    ("approved", "待支付"),
                    ("paid", "待收货"),
                    ("goods_received", "待开票"),
                    ("invoiced", "待验收"),
                    ("accepted", "待报销"),
                    ("inspection_skipped", "待报销 (无需验收)"),
                    ("reimbursed", "已报销"),
                    ("merged", "已合并"),
                    ("completed", "已完成"),
                ],
                max_length=30,
                null=True,
                verbose_name="合并前状态",
            ),
        ),
        migrations.AddField(
            model_name="requestitem",
            name="source_request",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="source_items",
                to="procurement.purchaserequest",
                verbose_name="合并前所属申请",
            ),
        ),
    ]
