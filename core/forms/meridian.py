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