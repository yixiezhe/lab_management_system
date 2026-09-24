from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("procurement", "0021_alter_publicprocurementdutyschedule_weekly_duty"),
    ]

    operations = [
        migrations.AddField(
            model_name="purchaserequest",
            name="actual_payment_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name="实际支付金额",
            ),
        ),
    ]
