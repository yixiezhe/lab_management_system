from datetime import date
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corridor_display", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="displayconfig",
            name="duty_week1_start",
            field=models.DateField(
                default=date(2025, 9, 15),
                verbose_name="值日第一周起始日期（周一）",
            ),
        ),
        migrations.AddField(
            model_name="displayconfig",
            name="package_duty_list",
            field=models.JSONField(
                blank=True,
                default=[
                    "示例成员01",
                    "示例成员02",
                    "示例成员03",
                    "示例成员04",
                    "示例成员05",
                    "示例成员06",
                    "示例成员07",
                    "示例成员08",
                    "示例成员09",
                    "示例成员10",
                    "示例成员11",
                    "示例成员12",
                    "示例成员13",
                    "示例成员14",
                    "示例成员15",
                    "示例成员16",
                    "示例成员17",
                    "示例成员18",
                ],
                verbose_name="取快递值日顺序（字符串数组）",
            ),
        ),
        migrations.AddField(
            model_name="displayconfig",
            name="lab_duty_groups",
            field=models.JSONField(
                blank=True,
                default=[
                    "第一组 (示例成员05、示例成员14、示例成员19)",
                    "第二组 (示例成员06、示例成员15、示例成员20)",
                    "第三组 (示例成员07、示例成员16、示例成员21)",
                    "第四组 (示例成员08、示例成员17、示例成员22)",
                    "第五组 (示例成员09、示例成员18、示例成员23)",
                    "第六组 (示例成员10、示例成员01、示例成员24)",
                    "第七组 (示例成员11、示例成员25)",
                    "第八组 (示例成员12、示例成员03、示例成员20)",
                    "第九组 (示例成员13、示例成员04、示例成员26)",
                ],
                verbose_name="卫生组轮值顺序（字符串数组）",
            ),
        ),
    ]
