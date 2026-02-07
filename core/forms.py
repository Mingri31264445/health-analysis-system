from django import forms
from .models import Questionnaire

class QuestionnaireForm(forms.ModelForm):
    class Meta:
        model = Questionnaire
        fields = [
            'name',
            'gender',
            'blood_type',
            'birth_date',
            'height',
            'weight',
            'sleep_hours', 
        ]
        widgets = {
            'name' : forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入姓名'
                }),
            'gender' : forms.Select(attrs={
                'class': 'form-select'
                }),
            'blood_type' : forms.Select(attrs={
                'class': 'form-select'
                }),
            'birth_date' : forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
                }),
            'height' : forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入身高（公分）'
                }),
            'weight' : forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入體重（公斤）'
                }),
            'sleep_hours' : forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入平均睡眠時間（小時）',
                'step': '0.5'
                }),
        }

from .models import MeridianTest

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
            'patient_name' : forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入病患姓名'
                }),
            'test_date' : forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
                }),
            'result_pdf' : forms.FileInput(attrs={
                'class': 'form-control',
                'accept':'.pdf'
                }),
            'notes' : forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': '備註(選填)',
                'rows': 3
                }),
        }

from .models import BFSTest

class BFSTestForm(forms.ModelForm):
    
    class Meta:
        model = BFSTest
        fields = [
            'patient_name',
            'test_date',
            'notes'
        ]
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

from .models import FaceDiagnosis

class FaceDiagnosisForm(forms.ModelForm):
    
    class Meta:
        model = FaceDiagnosis
        fields = ['patient_name', 'diagnosis_date', 'front_image', 'right_image', 'left_image', 'notes']
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