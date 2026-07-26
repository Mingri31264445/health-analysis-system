from django import forms

from ..models import BFSTest


class BFSTestForm(forms.ModelForm):
    class Meta:
        model = BFSTest
        fields = [
            'patient_name',
            'notes'
        ]
        labels = {
            "patient_name": "受測者姓名",
            "notes": "備註",
        }
        widgets = {
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入患者姓名'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備註（選填）'
            }),
        }


class BFSTestUpdateForm(forms.ModelForm):
    """編輯既有 BFSTest 的基本資料（PDF 檔案不可在此更換）。"""
    class Meta:
        model = BFSTest
        fields = ['patient_name', 'test_date', 'notes']
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
            # HTML datetime-local 只認得 %Y-%m-%dT%H:%M，需明確指定 format
            # 才能把既有 DateTimeField 值正確預填進輸入框
            'test_date': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                },
            ),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備註（選填）'
            }),
        }
