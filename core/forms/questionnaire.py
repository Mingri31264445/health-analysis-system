from django import forms

from ..models import Questionnaire


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
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入姓名'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'blood_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入身高（公分）'
            }),
            'weight': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入體重（公斤）'
            }),
            'sleep_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '請輸入平均睡眠時間（小時）',
                'step': '0.5'
            }),
        }