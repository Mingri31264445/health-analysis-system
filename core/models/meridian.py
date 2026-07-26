from django.db import models
from django.utils import timezone

# 經絡測試模型
class MeridianTest(models.Model):
    
    patient_name = models.CharField("患者姓名", max_length=100)
    test_date = models.DateTimeField(
        "測試日期",
        default = timezone.now
    )

    # 以下三欄由 PDF 解析後填入（birth_date 直接存字串，僅供顯示，不做排序/比對）
    gender = models.CharField("性別", max_length=10, blank=True)
    birth_date = models.CharField("生日", max_length=20, blank=True)
    age = models.FloatField("年齡", null=True, blank=True)

    # 測試結果PDF檔案
    result_pdf = models.FileField(
        "測試結果PDF",
        upload_to='meridian_tests/%Y/%m/%d/'# 上傳路徑會依照上傳日期自動分類
    )

    #儲存此報告的門檻值
    threshold_toohigh = models.FloatField("過高值", null=True, blank=True)
    threshold_high = models.FloatField("高值", null=True, blank=True)
    threshold_average = models.FloatField("均值", null=True, blank=True)
    threshold_low = models.FloatField("低值", null=True, blank=True)
    threshold_toolow = models.FloatField("過低值", null=True, blank=True)

    notes = models.TextField("備註", blank=True)

    created_at = models.DateTimeField("建立日期", auto_now_add=True)
    updated_at = models.DateTimeField("更新日期", auto_now=True)

    class Meta:
        verbose_name = "經絡測試"
        verbose_name_plural = "經絡測試列表"
        ordering = ['-test_date']# 設定資料撈出來時的排序依據

    def __str__(self):
        return f"{self.patient_name} - {self.test_date.strftime('%Y-%m-%d %H:%M')}"


class MeridianReading(models.Model):
    meridian_test = models.ForeignKey(MeridianTest, on_delete=models.CASCADE, related_name='readings')

    meridian = models.CharField("經絡名稱", max_length=50)

    left_org = models.FloatField("左側原始值")
    left_cmp = models.FloatField("左側比較值")
    right_org = models.FloatField("右側原始值")
    right_cmp = models.FloatField("右側比較值")

    class Meta:
        verbose_name = "經絡測試讀數"
        verbose_name_plural = "經絡測試讀數列表"

    def __str__(self):
        return f"{self.meridian_test.patient_name} - {self.meridian}"
