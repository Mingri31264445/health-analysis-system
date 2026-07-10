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