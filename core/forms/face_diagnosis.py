from django import forms

from ..models import FaceDiagnosis

MAX_IMAGE_SIZE = 15 * 1024 * 1024  # 單張照片上限 15 MB


def _check_size(image):
    if image and image.size > MAX_IMAGE_SIZE:
        raise forms.ValidationError('照片不可超過 15 MB。')
    return image


class FaceDiagnosisForm(forms.ModelForm):
    class Meta:
        model = FaceDiagnosis
        fields = ['front_image', 'right_image', 'left_image', 'notes']
        labels = {
            "front_image": "正面影像",
            "right_image": "右側影像（選填）",
            "left_image": "左側影像（選填）",
            "notes": "備註",
        }
        widgets = {
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

    def clean_front_image(self):
        return _check_size(self.cleaned_data.get('front_image'))

    def clean_right_image(self):
        return _check_size(self.cleaned_data.get('right_image'))

    def clean_left_image(self):
        return _check_size(self.cleaned_data.get('left_image'))


class FaceDiagnosisUpdateForm(forms.ModelForm):
    class Meta:
        model = FaceDiagnosis
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