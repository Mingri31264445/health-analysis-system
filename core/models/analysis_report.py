from django.conf import settings
from django.db import models


class AnalysisReport(models.Model):
    subject = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analysis_reports",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_analysis_reports",
    )
    questionnaire = models.ForeignKey(
        "core.Questionnaire", on_delete=models.SET_NULL, null=True, blank=True
    )
    face = models.ForeignKey(
        "core.FaceDiagnosis", on_delete=models.SET_NULL, null=True, blank=True
    )
    bfs = models.ForeignKey(
        "core.BFSTest", on_delete=models.SET_NULL, null=True, blank=True
    )
    meridian = models.ForeignKey(
        "core.MeridianTest", on_delete=models.SET_NULL, null=True, blank=True
    )
    selected_records = models.JSONField(default=dict)
    module_results = models.JSONField(default=dict)
    overall_result = models.CharField(max_length=6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-pk"]

    def __str__(self):
        return f"{self.subject_id} - {self.created_at:%Y-%m-%d %H:%M}"
