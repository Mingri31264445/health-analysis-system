from django.db import models
from django.utils import timezone

#量子生物回饋頻譜儀（BFS）測試模型
class BFSTest(models.Model):
    patient_name = models.CharField("患者姓名", max_length=100)
    test_date = models.DateTimeField(
        "測試日期",
        default=timezone.now
    )

    notes = models.TextField("備註", blank=True)

    needs_date_review = models.BooleanField(
        "日期需人工確認",
        default=False,
        help_text="上傳的多份 PDF 偵測到的日期彼此不一致，或完全無法辨識時會標記為 True"
    )

    created_at = models.DateTimeField("建立日期", auto_now_add=True)
    updated_at = models.DateTimeField("更新日期", auto_now=True)

    class Meta:
        verbose_name = "BFS測試"
        verbose_name_plural = "BFS測試列表"
        ordering = ['-test_date']# 設定資料撈出來時的排序依據

    def __str__(self):
        return f"{self.patient_name} - {self.test_date.strftime('%Y-%m-%d %H:%M')}"
    
# BFS測試相關檔案模型    
class BFSTestFile(models.Model):
    bfs_test  = models.ForeignKey(
        BFSTest,
        on_delete=models.CASCADE,
        related_name='files',
        verbose_name="BFS測試"
        )
    file_number = models.PositiveIntegerField("檔案編號")
    pdf_file = models.FileField(
        "PDF檔案",
        upload_to='bfs_tests/%Y/%m/%d/'# 上傳路徑會依照上傳日期自動分類
    )
    file_description = models.CharField("檔案描述", max_length=200, blank=True)

    detected_template = models.CharField("自動判斷模板", max_length=20, blank=True,)
    
    ANALYSIS_STATUS_CHOICES = [
        ("pending", "待分析"),
        ("success", "分析完成"),
        ("needs_review", "需人工確認"),
    ]
    analysis_status = models.CharField(
        "分析狀態", max_length=20,
        choices=ANALYSIS_STATUS_CHOICES, default="pending"
    )
    analysis_result = models.JSONField("分析結果", null=True, blank=True,)

    uploaded_at = models.DateTimeField("上傳日期", auto_now_add=True)

    class Meta:
        verbose_name = "BFS測試檔案"
        verbose_name_plural = "BFS測試檔案列表"
        ordering = ['bfs_test', 'file_number']# 設定資料撈出來時的排序依據

    def __str__(self):
        test_date = self.bfs_test.test_date.strftime('%Y-%m-%d')
        return f"{self.bfs_test.patient_name} ({test_date}) - 檔案 {self.file_number}"  