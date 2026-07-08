from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

from .models import BFSTest, FaceDiagnosis, MeridianTest, Questionnaire


PHONE_ERROR = "請輸入正確的手機號碼，例如：0912345678。"


def normalize_phone_number(value):
    digits = "".join(char for char in str(value or "") if char.isdigit())
    if digits.startswith("886") and len(digits) == 12:
        digits = f"0{digits[3:]}"
    return digits


def is_valid_phone_number(value):
    return len(value) == 10 and value.startswith("09") and value.isdigit()


class RegisterForm(UserCreationForm):
    username = forms.CharField(
        label="手機號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例如：0912345678",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )
    email = forms.EmailField(
        label="電子信箱",
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "example@email.com",
                "autocomplete": "email",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
        labels = {
            "username": "手機號碼",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "密碼"
        self.fields["password2"].label = "確認密碼"
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "請輸入密碼", "autocomplete": "new-password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "請再次輸入密碼", "autocomplete": "new-password"}
        )

    def clean_username(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("username"))
        if not is_valid_phone_number(phone_number):
            raise forms.ValidationError(PHONE_ERROR)
        if User.objects.filter(username=phone_number).exists():
            raise forms.ValidationError("這支手機號碼已經註冊過，請直接登入。")
        return phone_number


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "手機號碼或密碼不正確，請再確認一次。",
        "inactive": "此帳號目前無法使用。",
    }
    username = forms.CharField(
        label="手機號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例如：0912345678",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )
    password = forms.CharField(
        label="密碼",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "請輸入密碼", "autocomplete": "current-password"}
        ),
    )
    remember_me = forms.BooleanField(
        label="讓我保持登入",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "remember-checkbox"}),
    )

    def clean_username(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("username"))
        if not is_valid_phone_number(phone_number):
            raise forms.ValidationError(PHONE_ERROR)
        return phone_number


class PhonePasswordResetForm(forms.Form):
    phone_number = forms.CharField(
        label="手機號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "請輸入註冊時使用的手機號碼",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )
    new_password1 = forms.CharField(
        label="新密碼",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "請輸入新密碼", "autocomplete": "new-password"}
        ),
    )
    new_password2 = forms.CharField(
        label="確認新密碼",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "請再次輸入新密碼", "autocomplete": "new-password"}
        ),
    )

    def clean_phone_number(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("phone_number"))
        if not is_valid_phone_number(phone_number):
            raise forms.ValidationError(PHONE_ERROR)

        self.user = User.objects.filter(username=phone_number).first()
        if self.user is None:
            raise forms.ValidationError("查無此手機號碼，請先建立帳號。")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "兩次輸入的密碼不一致。")

        if password1 and hasattr(self, "user"):
            validate_password(password1, self.user)

        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user


class QuestionnaireForm(forms.ModelForm):
    SECTION_DEFINITIONS = [
        {
            "step": "01",
            "title": "個人資料",
            "description": "請填寫受測者基本資料，作為後續健康分析的基礎。",
            "fields": ["name", "gender", "birth_date", "blood_type", "height", "weight"],
        },
        {
            "step": "02",
            "title": "過去病史",
            "description": "請勾選曾經診斷或目前仍在追蹤的相關疾病。若無相關狀況，可直接略過。",
            "fields": [
                "autoimmune_disease",
                "cardiovascular_disease",
                "diabetes",
                "chronic_hepatitis",
                "heart_disease",
                "heart_valve_insufficiency",
                "liver_cirrhosis",
                "liver_disease",
                "spleen_enlarged",
                "lung_tuberculosis",
                "lung_asthma",
                "lung_inflammation",
                "lung_covid19",
                "kidney_disease",
                "kidney_stone",
                "hemodialysis",
                "stomach_ulcer",
                "stomach_reflux",
                "intestine_inflammation",
                "intestine_disease",
                "gallbladder_stone",
                "gallbladder_inflammation",
                "bladder_stone",
                "bladder_inflammation",
                "uterine_inflammation",
                "uterine_tumor",
                "uterine_syndrome",
                "other_chronic",
                "other_cancer",
                "other_nerve",
                "other_disease",
            ],
        },
        {
            "step": "03",
            "title": "過敏與不良嗜好",
            "description": "請補充過敏原與日常嗜好，協助平台建立更完整的健康背景。",
            "fields": [
                "allergy_food",
                "allergy_drug",
                "allergy_other",
                "habit_smoking",
                "habit_alcohol",
                "habit_betel",
                "habit_late_sleep",
                "habit_other",
            ],
        },
        {
            "step": "04",
            "title": "生活習慣",
            "description": "請填寫睡眠、運動與生理期資訊，作為狀態判讀的參考。",
            "fields": ["sleep_hours", "exercise", "exercise_duration", "exercise_frequency", "menstruation"],
        },
        {
            "step": "05",
            "title": "手術史與備註",
            "description": "若有手術或其他需補充的症狀，可在此填寫。",
            "fields": ["surgery_history", "surgery_1", "surgery_2", "notes"],
        },
    ]

    class Meta:
        model = Questionnaire
        fields = [
            "name",
            "gender",
            "blood_type",
            "birth_date",
            "height",
            "weight",
            "autoimmune_disease",
            "cardiovascular_disease",
            "diabetes",
            "chronic_hepatitis",
            "heart_disease",
            "heart_valve_insufficiency",
            "liver_cirrhosis",
            "liver_disease",
            "spleen_enlarged",
            "lung_tuberculosis",
            "lung_asthma",
            "lung_inflammation",
            "lung_covid19",
            "kidney_disease",
            "kidney_stone",
            "hemodialysis",
            "stomach_ulcer",
            "stomach_reflux",
            "intestine_inflammation",
            "intestine_disease",
            "gallbladder_stone",
            "gallbladder_inflammation",
            "bladder_stone",
            "bladder_inflammation",
            "uterine_inflammation",
            "uterine_tumor",
            "uterine_syndrome",
            "other_chronic",
            "other_cancer",
            "other_nerve",
            "other_disease",
            "allergy_food",
            "allergy_drug",
            "allergy_other",
            "habit_smoking",
            "habit_alcohol",
            "habit_betel",
            "habit_late_sleep",
            "habit_other",
            "sleep_hours",
            "exercise",
            "exercise_duration",
            "exercise_frequency",
            "menstruation",
            "surgery_history",
            "surgery_1",
            "surgery_2",
            "notes",
        ]
        labels = {
            "name": "姓名",
            "gender": "性別",
            "blood_type": "血型",
            "birth_date": "出生日期",
            "height": "身高（cm）",
            "weight": "體重（kg）",
            "stomach_ulcer": "胃炎 / 胃潰瘍",
            "exercise": "有運動習慣",
            "exercise_duration": "每次運動時間（分鐘/天）",
            "exercise_frequency": "每週運動頻率",
            "menstruation": "生理期（女性適用）",
            "surgery_history": "有手術史",
            "surgery_1": "手術名稱 1",
            "surgery_2": "手術名稱 2",
            "sleep_hours": "每日睡眠時數",
            "notes": "其他備註",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "請輸入姓名"}),
            "gender": forms.Select(attrs={"class": "form-select"}),
            "blood_type": forms.Select(attrs={"class": "form-select"}),
            "birth_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "height": forms.NumberInput(attrs={"class": "form-control", "placeholder": "例如：165"}),
            "weight": forms.NumberInput(attrs={"class": "form-control", "placeholder": "例如：55"}),
            "other_chronic": forms.Textarea(attrs={"class": "form-control", "placeholder": "例如：甲狀腺疾病、高血壓等", "rows": 2}),
            "other_cancer": forms.Textarea(attrs={"class": "form-control", "placeholder": "若有癌症病史請補充", "rows": 2}),
            "other_nerve": forms.Textarea(attrs={"class": "form-control", "placeholder": "若有神經系統疾病請補充", "rows": 2}),
            "other_disease": forms.Textarea(attrs={"class": "form-control", "placeholder": "其他未列出的疾病或症狀", "rows": 2}),
            "allergy_food": forms.Textarea(attrs={"class": "form-control", "placeholder": "例如：海鮮、堅果、牛奶", "rows": 2}),
            "allergy_drug": forms.Textarea(attrs={"class": "form-control", "placeholder": "例如：抗生素、止痛藥", "rows": 2}),
            "allergy_other": forms.Textarea(attrs={"class": "form-control", "placeholder": "例如：塵蟎、花粉、乳膠", "rows": 2}),
            "habit_other": forms.Textarea(attrs={"class": "form-control", "placeholder": "其他生活嗜好或作息狀況", "rows": 2}),
            "sleep_hours": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "例如：7.5", "step": "0.5"}
            ),
            "exercise_duration": forms.NumberInput(
                attrs={"class": "form-control", "placeholder": "例如：30", "min": "0", "max": "1440"}
            ),
            "exercise_frequency": forms.Select(attrs={"class": "form-select"}),
            "surgery_1": forms.TextInput(attrs={"class": "form-control", "placeholder": "例如：闌尾切除手術"}),
            "surgery_2": forms.TextInput(attrs={"class": "form-control", "placeholder": "可留空"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "placeholder": "若以上症狀或狀況不足以描述，可在此補充", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gender"].choices = [("", "請選擇性別"), ("M", "男"), ("F", "女")]
        self.fields["blood_type"].choices = [("", "請選擇血型"), ("A", "A型"), ("B", "B型"), ("AB", "AB型"), ("O", "O型")]
        self.fields["exercise_frequency"].choices = [("", "請選擇頻率")] + list(
            self.fields["exercise_frequency"].choices
        )

        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "health-checkbox"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("class", "form-control")
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault("class", "form-select")
            else:
                field.widget.attrs.setdefault("class", "form-control")

            if name in {"exercise_duration", "exercise_frequency"}:
                field.required = False

    def get_sections(self):
        sections = []
        for section in self.SECTION_DEFINITIONS:
            sections.append(
                {
                    "step": section["step"],
                    "title": section["title"],
                    "description": section["description"],
                    "fields": [self[field_name] for field_name in section["fields"]],
                }
            )
        return sections


class MeridianTestForm(forms.ModelForm):
    class Meta:
        model = MeridianTest
        fields = ["patient_name", "test_date", "result_pdf", "notes"]
        labels = {
            "patient_name": "受測者姓名",
            "test_date": "檢測時間",
            "result_pdf": "檢測結果 PDF",
            "notes": "備註",
        }
        widgets = {
            "patient_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "請輸入受測者姓名"}),
            "test_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "result_pdf": forms.FileInput(attrs={"class": "form-control", "accept": ".pdf"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "placeholder": "可填寫補充說明", "rows": 3}),
        }


class BFSTestForm(forms.ModelForm):
    class Meta:
        model = BFSTest
        fields = ["patient_name", "test_date", "notes"]
        labels = {
            "patient_name": "受測者姓名",
            "test_date": "檢測時間",
            "notes": "備註",
        }
        widgets = {
            "patient_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "請輸入受測者姓名"}),
            "test_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "可填寫補充說明"}),
        }


class FaceDiagnosisForm(forms.ModelForm):
    class Meta:
        model = FaceDiagnosis
        fields = ["patient_name", "diagnosis_date", "front_image", "right_image", "left_image", "notes"]
        labels = {
            "patient_name": "受測者姓名",
            "diagnosis_date": "拍攝時間",
            "front_image": "正面影像",
            "right_image": "右側影像",
            "left_image": "左側影像",
            "notes": "備註",
        }
        widgets = {
            "patient_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "請輸入受測者姓名"}),
            "diagnosis_date": forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
            "front_image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "right_image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "left_image": forms.FileInput(attrs={"class": "form-control", "accept": "image/*"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "可填寫補充說明"}),
        }
