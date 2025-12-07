from django.db import models
from django.utils import timezone

# 面診系統模型
class FaceDiagnosis(models.Model):
    patient_name = models.CharField("患者姓名", max_length=100)
    diagnosis_date = models.DateTimeField(
        "診斷日期",
        default=timezone.now
    )

    front_image = models.ImageField(
        "正面照片",
        upload_to='face_diagnosis/%Y/%m/%d/front/'# 上傳路徑會依照上傳日期自動分類
    )
    right_image = models.ImageField(
        "右側照片",
        upload_to='face_diagnosis/%Y/%m/%d/right/'# 上傳路徑會依照上傳日期自動分類
    )

    left_image = models.ImageField(
        "左側照片",
        upload_to='face_diagnosis/%Y/%m/%d/left/'# 上傳路徑會依照上傳日期自動分類
    )

    analysis_report = models.JSONField(
        "分析報告",
        default=dict,
        blank=True,
        help_text="存儲面診分析結果的JSON資料"
    )

    notes = models.TextField("備註", blank=True)

    created_at = models.DateTimeField("建立日期", auto_now_add=True)
    updated_at = models.DateTimeField("更新日期", auto_now=True)

    class Meta:
        verbose_name = "面診系統"
        verbose_name_plural = "面診系統列表"
        ordering = ['-diagnosis_date']# 設定資料撈出來時的排序依據

    def __str__(self):
        return f"{self.patient_name} - {self.diagnosis_date.strftime('%Y-%m-%d %H:%M')}"