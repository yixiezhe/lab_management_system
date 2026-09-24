# Generated manually for PDF invoice uploads.

import invoice.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("invoice", "0004_alter_invoice_purchase_request"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoice",
            name="invoice_image",
            field=models.FileField(
                upload_to="invoices/%Y/%m/%d/",
                validators=[invoice.models.validate_invoice_file],
                verbose_name="发票截图",
            ),
        ),
    ]
