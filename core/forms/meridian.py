from django import forms

from ..models import MeridianTest


class MeridianTestForm(forms.ModelForm):
    class Meta:
        model = MeridianTest
        # patient_name、test_date 改由 PDF 解析後填入，不再由使用者手動輸入
        fields = [
            'result_pdf',
            'notes',
        ]
        labels = {
            "result_pdf": "檢測結果 PDF",
            "notes": "備註",
        }
        widgets = {
            'result_pdf': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '備註(選填)',
                'rows': 3
            }),
        }


class MeridianTestUpdateForm(forms.ModelForm):
    """編輯既有經絡記錄。只開放備註——其餘個資皆以 PDF 解析為準，不讓管理者手動覆蓋。"""
    class Meta:
        model = MeridianTest
        fields = ['notes']
        labels = {
            "notes": "備註",
        }
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備註（選填）'
            }),
        }