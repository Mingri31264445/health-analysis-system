from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError #  用於跨欄位的邏輯驗證

# AI 人工智慧臉部影像整併系統開發問卷模型
class Questionnaire(models.Model):

    # 基本資料
    name  = models.CharField("姓名", max_length=100)
    gender = models.CharField("性別", max_length=10, choices=[
        ('M', '男'), 
        ('F', '女')
        ])
    blood_type = models.CharField("血型", max_length=3, choices=[
        ('A', 'A型'), 
        ('B', 'B型'), 
        ('AB', 'AB型'), 
        ('O', 'O型')
        ])
    height = models.FloatField("身高(cm)")
    weight = models.FloatField("體重(kg)")
    birth_date = models.DateField("出生日期")

    # 過去病史
    # 慢性病
    autoimmune_disease = models.BooleanField("自體免疫疾病", default=False)
    cardiovascular_disease = models.BooleanField("心血管疾病", default=False)
    diabetes = models.BooleanField("糖尿病", default=False)
    chronic_hepatitis = models.BooleanField("慢性肝炎", default=False)

    # 心臟疾病
    heart_disease = models.BooleanField("心臟疾病", default=False)
    heart_valve_insufficiency = models.BooleanField("心臟瓣膜閉鎖不全", default=False)
    # 肝臟疾病
    liver_cirrhosis = models.BooleanField("肝硬化", default=False)
    liver_disease = models.BooleanField("肝臟病", default=False)

    # 脾臟疾病
    spleen_enlarged = models.BooleanField("脾臟腫大", default=False)

    # 肺部疾病
    lung_tuberculosis = models.BooleanField("肺結核", default=False)
    lung_asthma = models.BooleanField("氣喘", default=False)
    lung_inflammation = models.BooleanField("肺炎", default=False)
    lung_covid19 = models.BooleanField("COVID-19", default=False)

    # 腎臟疾病
    kidney_disease = models.BooleanField("腎臟病", default=False)
    kidney_stone = models.BooleanField("腎結石", default=False)
    hemodialysis = models.BooleanField("洗腎", default=False)#血液透析

    # 胃部疾病
    stomach_ulcer = models.BooleanField("胃炎", default=False)
    stomach_reflux = models.BooleanField("逆流性食道炎", default=False)

    # 大腸小腸疾病
    intestine_inflammation = models.BooleanField("發炎性腸道疾病", default=False)
    intestine_disease = models.BooleanField("腸躁症", default=False)

    # 膽囊疾病
    gallbladder_stone = models.BooleanField("膽結石", default=False)
    gallbladder_inflammation = models.BooleanField("膽囊炎", default=False)

    # 膀胱疾病
    bladder_stone = models.BooleanField("膀胱結石", default=False)
    bladder_inflammation = models.BooleanField("膀胱炎", default=False)

    # 卵巢子宮疾病
    uterine_inflammation = models.BooleanField("骨盆腔炎", default=False)
    uterine_tumor = models.BooleanField("子宮肌瘤", default=False)
    uterine_syndrome = models.BooleanField("子宮肌腺症", default=False)

    # 其他疾病
    other_chronic = models.TextField("其他慢性疾病", blank=True)
    other_cancer = models.TextField("其他癌症", blank=True)
    other_nerve = models.TextField("其他神經疾病", blank=True)
    other_disease = models.TextField("其他疾病", blank=True)

    # 過敏原
    allergy_food = models.TextField("食物過敏原", blank=True)
    allergy_drug = models.TextField("藥物過敏原", blank=True)
    allergy_other = models.TextField("其他過敏原", blank=True)

    # 不良嗜好
    habit_smoking = models.BooleanField("吸菸", default=False)
    habit_alcohol = models.BooleanField("喝酒", default=False)
    habit_betel = models.BooleanField("嚼檳榔", default=False)
    habit_late_sleep = models.BooleanField("熬夜", default=False)
    habit_other = models.TextField("其他不良嗜好", blank=True)

    # 生活習慣
    sleep_hours = models.FloatField("平均睡眠時間(小時/天)")
    exercise = models.BooleanField("運動習慣", default=False)
    exercise_duration = models.FloatField(
        "每次運動時間(分鐘/天)",
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1440)]
    )
    exercise_frequency = models.PositiveSmallIntegerField(
        "每週運動頻率(幾天/週)",
        choices=[(i, f'{i}天') for i in range(1, 8)],
        null=True,
        blank=True,
        help_text='請選擇每週運動 1-7 天'
    )
    menstruation = models.BooleanField("生理期(女性適用)", default=False)

    # 手術史
    surgery_history = models.BooleanField("是否有手術史", default=False)
    surgery_1 = models.CharField("1.手術詳情", max_length=200, blank=True)
    surgery_2 = models.CharField("2.手術詳情", max_length=200, blank=True)

    # 備註
    notes = models.TextField("其他備註", blank=True)

    created_at = models.DateTimeField("填寫日期", auto_now_add=True)
    updated_at = models.DateTimeField("更新日期", auto_now=True)

    def clean(self):
        super().clean()
        errors = {}

        #性別與生理期的邏輯驗證
        if self.gender == 'M' and self.menstruation:
            errors['menstruation'] = '男性不能勾選生理期選項'

        #運動習慣與運動頻率的邏輯驗證
        if not self.exercise:
            if self.exercise_duration:
                errors['exercise_duration'] = '您未勾選「有運動習慣」，請勿填寫運動時間'
            if self.exercise_frequency:
                errors['exercise_frequency'] = '您未勾選「有運動習慣」，請勿填寫運動頻率'
        else:
            if not self.exercise_duration:
                errors['exercise_duration'] = '您勾選了「有運動習慣」，請填寫每次運動時間'
            if not self.exercise_frequency:
                errors['exercise_frequency'] = '您勾選了「有運動習慣」，請填寫每週運動頻率'

        #手術史的邏輯驗證
        details = [self.surgery_1, self.surgery_2]

        if not self.surgery_history:
            if any(details):
                errors['surgery_1'] = '您未勾選「有手術史」，請勿填寫手術詳情'
        else:
            if not any(details):
                errors['surgery_1'] = '您勾選了「有手術史」，請至少填寫一項手術詳情'

        if errors:
            raise ValidationError(errors)
        
    def save(self, *args, **kwargs):
        self.full_clean()  # 在保存前進行驗證
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "問卷"
        verbose_name_plural = "問卷列表"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.created_at.strftime('%Y-%m-%d')}"