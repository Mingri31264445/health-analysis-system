from django import forms

from ..models import BFSTest


class BFSTestForm(forms.ModelForm):
    class Meta:
        model = BFSTest
        fields = [
            'patient_name',
            'test_date',
            'notes'
        ]
        labels = {
            "patient_name": "受測者姓名",
            "test_date": "檢測時間",
            "notes": "備註",
        }
        widgets = {
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入患者姓名'
            }),
            'test_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備註（選填）'
            }),
        }

    # 修改表單初始化方法，管理者不填日期直接送出是合法的
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['test_date'].required = False
        self.fields['test_date'].help_text = (
            "若留空，系統將嘗試從上傳的 PDF 自動辨識日期；"
            "PDF 無法辨識時才需要手動輸入。"
        )