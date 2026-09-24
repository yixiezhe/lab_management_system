from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("reimbursement", "0002_reimbursement"),
    ]

    operations = [
        migrations.AddField(
            model_name="reimbursement",
            name="actual_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                max_digits=10,
                null=True,
                verbose_name="报销实际金额",
            ),
        ),
    ]

