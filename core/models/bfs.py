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

    uploaded_at = models.DateTimeField("上傳日期", auto_now_add=True)

    class Meta:
        verbose_name = "BFS測試檔案"
        verbose_name_plural = "BFS測試檔案列表"
        ordering = ['bfs_test', 'file_number']# 設定資料撈出來時的排序依據

    def __str__(self):
        test_date = self.bfs_test.test_date.strftime('%Y-%m-%d')
        return f"{self.bfs_test.patient_name} ({test_date}) - 檔案 {self.file_number}"  