from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("group_affairs", "0001_initial"),
    ]

    operations = [
        migrations.AddField(model_name="groupaffairboard", name="purchase_rotation", field=models.JSONField(blank=True, default=list, verbose_name="采购轮班名单")),
        migrations.AddField(model_name="groupaffairboard", name="purchase_rotation_index", field=models.PositiveIntegerField(default=0, verbose_name="下次采购轮班序号")),
        migrations.CreateModel(
            name="GroupPurchase",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("items", models.TextField(verbose_name="采购物品")),
                ("note", models.TextField(blank=True, verbose_name="备注")),
                ("status", models.CharField(choices=[("assigned", "待购买"), ("paid", "已支付"), ("arrived", "已到货"), ("reimbursed", "已报销")], default="assigned", max_length=20, verbose_name="状态")),
                ("payment_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name="支付金额")),
                ("payment_proof", models.FileField(blank=True, upload_to="group_purchases/payment/%Y/%m/", verbose_name="支付凭证")),
                ("invoice", models.FileField(blank=True, upload_to="group_purchases/invoice/%Y/%m/", verbose_name="发票")),
                ("item_image", models.ImageField(blank=True, upload_to="group_purchases/items/%Y/%m/", verbose_name="实物图片")),
                ("paid_at", models.DateTimeField(blank=True, null=True, verbose_name="支付时间")),
                ("arrived_at", models.DateTimeField(blank=True, null=True, verbose_name="到货登记时间")),
                ("reimbursed_at", models.DateTimeField(blank=True, null=True, verbose_name="报销完成时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="发起时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("board", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="purchases", to="group_affairs.groupaffairboard", verbose_name="小组事务板")),
                ("buyer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="assigned_group_purchases", to=settings.AUTH_USER_MODEL, verbose_name="采购人")),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="requested_group_purchases", to=settings.AUTH_USER_MODEL, verbose_name="请购人")),
            ],
            options={"verbose_name": "组内采购", "verbose_name_plural": "组内采购", "ordering": ["-created_at", "-id"]},
        ),
        migrations.CreateModel(
            name="GroupPurchasePopupRead",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reminder_type", models.CharField(choices=[("assigned", "采购分配提醒"), ("reimbursement", "报销提醒")], max_length=20, verbose_name="提醒类型")),
                ("reminder_date", models.DateField(verbose_name="提醒日期")),
                ("read_at", models.DateTimeField(auto_now=True, verbose_name="确认时间")),
                ("purchase", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="popup_reads", to="group_affairs.grouppurchase", verbose_name="采购单")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="group_purchase_popup_reads", to=settings.AUTH_USER_MODEL, verbose_name="用户")),
            ],
            options={"verbose_name": "组内采购弹窗确认", "verbose_name_plural": "组内采购弹窗确认"},
        ),
        migrations.AddConstraint(model_name="grouppurchasepopupread", constraint=models.UniqueConstraint(fields=("purchase", "user", "reminder_type", "reminder_date"), name="unique_group_purchase_popup_read")),
    ]
