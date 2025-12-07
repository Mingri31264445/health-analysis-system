from django.db import models
from django.utils import timezone

# 經絡測試模型
class MeridianTest(models.Model):
    
    patient_name = models.CharField("患者姓名", max_length=100)
    test_date = models.DateTimeField(
        "測試日期",
        default = timezone.now
    )

    # 測試結果PDF檔案
    result_pdf = models.FileField(
        "測試結果PDF",
        upload_to='meridian_tests/%Y/%m/%d/'# 上傳路徑會依照上傳日期自動分類
    )

    notes = models.TextField("備註", blank=True)

    created_at = models.DateTimeField("建立日期", auto_now_add=True)
    updated_at = models.DateTimeField("更新日期", auto_now=True)

    class Meta:
        verbose_name = "經絡測試"
        verbose_name_plural = "經絡測試列表"
        ordering = ['-test_date']# 設定資料撈出來時的排序依據

    def __str__(self):
        return f"{self.patient_name} - {self.test_date.strftime('%Y-%m-%d %H:%M')}"