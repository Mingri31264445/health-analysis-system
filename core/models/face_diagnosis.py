from django.conf import settings
from django.db import models
from django.utils import timezone

# 面診系統模型
class FaceDiagnosis(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_PENDING, '待分析'),
        (STATUS_DONE, '完成'),
        (STATUS_FAILED, '失敗'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="face_diagnoses",
        null=True,
        blank=True,
        verbose_name="使用者",
    )
    patient_name = models.CharField("患者姓名", max_length=100)
    diagnosis_date = models.DateTimeField(
        "診斷日期",
        default=timezone.now
    )

    front_image = models.ImageField(
        "正面照片",
        upload_to='face_diagnosis/%Y/%m/%d/front/'# 上傳路徑會依照上傳日期自動分類
    )
    # 側臉照目前不做分析，改為選填
    right_image = models.ImageField(
        "右側照片",
        upload_to='face_diagnosis/%Y/%m/%d/right/',# 上傳路徑會依照上傳日期自動分類
        blank=True,
    )

    left_image = models.ImageField(
        "左側照片",
        upload_to='face_diagnosis/%Y/%m/%d/left/',# 上傳路徑會依照上傳日期自動分類
        blank=True,
    )

    analysis_report = models.JSONField(
        "分析報告",
        default=dict,
        blank=True,
        help_text="存儲面診分析結果的JSON資料"
    )

    # 分析狀態：待分析 / 完成 / 失敗
    analysis_status = models.CharField(
        "分析狀態",
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    analysis_error = models.TextField("分析錯誤訊息", blank=True)
    analyzed_at = models.DateTimeField("分析完成時間", null=True, blank=True)

    notes = models.TextField("備註", blank=True)

    created_at = models.DateTimeField("建立日期", auto_now_add=True)
    updated_at = models.DateTimeField("更新日期", auto_now=True)

    class Meta:
        verbose_name = "面診系統"
        verbose_name_plural = "面診系統列表"
        ordering = ['-diagnosis_date']# 設定資料撈出來時的排序依據

    def __str__(self):
        return f"{self.patient_name} - {self.diagnosis_date.strftime('%Y-%m-%d %H:%M')}"