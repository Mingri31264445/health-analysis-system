from django import forms

from ..models import FaceDiagnosis


class FaceDiagnosisForm(forms.ModelForm):
    class Meta:
        model = FaceDiagnosis
        fields = ['patient_name', 'diagnosis_date', 'front_image', 'right_image', 'left_image', 'notes']
        labels = {
            "patient_name": "受測者姓名",
            "diagnosis_date": "拍攝時間",
            "front_image": "正面影像",
            "right_image": "右側影像",
            "left_image": "左側影像",
            "notes": "備註",
        }
        widgets = {
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入患者姓名'
            }),
            'diagnosis_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'front_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'right_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'left_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '備註（選填）'
            }),
        }