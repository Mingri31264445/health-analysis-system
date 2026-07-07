from django import forms

from ..models import MeridianTest


class MeridianTestForm(forms.ModelForm):
    class Meta:
        model = MeridianTest
        fields = [
            'patient_name',
            'test_date',
            'result_pdf',
            'notes',
        ]
        widgets = {
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入病患姓名'
            }),
            'test_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
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