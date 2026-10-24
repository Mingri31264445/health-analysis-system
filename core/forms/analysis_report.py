from django import forms

from ..models import BFSTest, FaceDiagnosis, MeridianTest, Questionnaire


class AnalysisRecordForm(forms.Form):
    questionnaire = forms.ModelChoiceField(
        label="健康問卷", queryset=Questionnaire.objects.none(), required=False
    )
    face = forms.ModelChoiceField(
        label="面診影像", queryset=FaceDiagnosis.objects.none(), required=False
    )
    bfs = forms.ModelChoiceField(
        label="BFS 檢測", queryset=BFSTest.objects.none(), required=False
    )
    meridian = forms.ModelChoiceField(
        label="經絡儀檢測", queryset=MeridianTest.objects.none(), required=False
    )

    def __init__(self, *args, subject, selected=None, **kwargs):
        super().__init__(*args, **kwargs)
        querysets = {
            "questionnaire": Questionnaire.objects.filter(user=subject).order_by("-updated_at", "-pk"),
            "face": FaceDiagnosis.objects.filter(user=subject).order_by("-diagnosis_date", "-pk"),
            "bfs": BFSTest.objects.filter(user=subject).order_by("-test_date", "-pk"),
            "meridian": MeridianTest.objects.filter(user=subject).order_by("-test_date", "-pk"),
        }
        for key, queryset in querysets.items():
            field = self.fields[key]
            field.queryset = queryset
            field.empty_label = (
                f"此帳號尚無 {field.label}紀錄"
                if not queryset.exists() else "不選用這項資料"
            )
            field.widget.attrs["class"] = "result-select"
            field.label_from_instance = self._choice_label
            if not self.is_bound:
                self.initial[key] = (
                    selected.get(key) if selected is not None else queryset.first()
                )

    @staticmethod
    def _choice_label(obj):
        date = getattr(obj, "updated_at", None) or getattr(obj, "diagnosis_date", None)
        date = date or getattr(obj, "test_date", None)
        return f"{date:%Y/%m/%d %H:%M} · #{obj.pk}"
