from django.db import models
from django.db.models import Max
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date


def default_package_duty_list():
    return [
        "示例成员01", "示例成员02", "示例成员03", "示例成员04", "示例成员05", "示例成员06",
        "示例成员07", "示例成员08", "示例成员09", "示例成员10", "示例成员11", "示例成员12",
        "示例成员13", "示例成员14", "示例成员15", "示例成员16", "示例成员17", "示例成员18"
    ]


def default_lab_duty_groups():
    return [
        "第一组 (示例成员05、示例成员14、示例成员19)",
        "第二组 (示例成员06、示例成员15、示例成员20)",
        "第三组 (示例成员07、示例成员16、示例成员21)",
        "第四组 (示例成员08、示例成员17、示例成员22)",
        "第五组 (示例成员09、示例成员18、示例成员23)",
        "第六组 (示例成员10、示例成员01、示例成员24)",
        "第七组 (示例成员11、示例成员25)",
        "第八组 (示例成员12、示例成员03、示例成员20)",
        "第九组 (示例成员13、示例成员04、示例成员26)",
    ]


class DisplayImage(models.Model):
    """
    走廊显示屏轮播图片
    """
    image = models.ImageField(upload_to='corridor_display/images/', verbose_name='图片文件')
    name = models.CharField(max_length=255, blank=True, default='', verbose_name='图片名称/备注')
    order = models.PositiveIntegerField(default=0, db_index=True, verbose_name='排序号（越小越靠前）')

    # 可选：用于前端展示（如果 Pillow 可用会自动写入）
    width = models.PositiveIntegerField(null=True, blank=True, verbose_name='宽')
    height = models.PositiveIntegerField(null=True, blank=True, verbose_name='高')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '走廊显示图片'
        verbose_name_plural = verbose_name
        ordering = ['order', 'created_at']

    def __str__(self):
        return f'#{self.order} {self.name or self.image.name}'

    def save(self, *args, **kwargs):
        # 自动给新图片排到最后
        if self.pk is None and (self.order is None or self.order == 0):
            max_order = DisplayImage.objects.aggregate(m=Max('order')).get('m') or 0
            self.order = max_order + 1

        # 自动读取宽高（如果 Pillow 存在）
        try:
            if self.image and (not self.width or not self.height):
                from PIL import Image as PILImage
                self.image.open()
                with PILImage.open(self.image) as im:
                    self.width, self.height = im.size
        except Exception:
            # Pillow 不存在或图片异常时不影响保存
            pass

        super().save(*args, **kwargs)


class DisplayConfig(models.Model):
    """
    走廊显示屏配置（单例表：只保留一行）
    """
    carousel_interval_ms = models.PositiveIntegerField(
        default=5000,
        validators=[MinValueValidator(1000), MaxValueValidator(60000)],
        verbose_name='轮播间隔（毫秒）'
    )

    state = models.CharField(max_length=100, default='运行正常', verbose_name='当前状态')
    tip = models.CharField(max_length=255, default='请保持实验台整洁，离开前确认电源/气源关闭。', verbose_name='今日提示')
    safety = models.CharField(max_length=255, default='通风橱使用后请复位；废液按规定分类。', verbose_name='安全检查')
    notes = models.JSONField(default=list, blank=True, verbose_name='补充说明（字符串数组）')
    duty_text = models.TextField(default='', blank=True, verbose_name='值日安排文本')
    duty_week1_start = models.DateField(
        default=date(2025, 9, 15),
        verbose_name='值日第一周起始日期（周一）'
    )
    duty_rotation_unit = models.CharField(
        max_length=4,
        choices=[('week', '按周'), ('day', '按天')],
        default='week',
        verbose_name='值日轮换周期'
    )
    package_duty_list = models.JSONField(
        default=default_package_duty_list,
        blank=True,
        verbose_name='取快递值日顺序（字符串数组）'
    )
    lab_duty_groups = models.JSONField(
        default=default_lab_duty_groups,
        blank=True,
        verbose_name='卫生组轮值顺序（字符串数组）'
    )

    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '走廊显示配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return '走廊显示配置'

    @classmethod
    def get_solo(cls):
        """
        获取单例配置（不存在就创建）
        """
        obj, _ = cls.objects.get_or_create(id=1)
        return obj
