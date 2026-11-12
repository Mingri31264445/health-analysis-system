from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from ..forms.analysis_report import AnalysisRecordForm
from ..models import AnalysisReport
from ..services.analysis_report import MODULES, build_report_data
from ..services.subjects import get_subject_contact_line, get_subject_display_name
from .dashboard import get_subject_user_queryset
from .permissions import can_manage_all_records, can_view_all_records
from .workflow_navigation import workflow_navigation


@login_required(login_url="login")
def analysis_report_view(request, subject_id):
    subject = get_object_or_404(
        get_subject_user_queryset(request.user, can_view_all_records(request.user)),
        pk=subject_id,
    )
    can_save = request.user.pk == subject.pk or can_manage_all_records(request.user)
    reports = AnalysisReport.objects.filter(subject=subject)
    report = None
    is_preview = False
    if request.method == "GET" and request.GET.get("report"):
        report = get_object_or_404(reports, pk=request.GET["report"])

    selected = None
    if report is not None:
        selected = {
            key: getattr(report, key) for key, _label in MODULES
        }

    if request.method == "POST":
        if not can_save:
            raise PermissionDenied
        form = AnalysisRecordForm(request.POST, subject=subject)
        if form.is_valid():
            selected = form.cleaned_data
            records, results, overall = build_report_data(selected)
            report = AnalysisReport.objects.create(
                subject=subject,
                created_by=request.user,
                questionnaire=selected["questionnaire"],
                face=selected["face"],
                bfs=selected["bfs"],
                meridian=selected["meridian"],
                selected_records=records,
                module_results=results,
                overall_result=overall,
            )
            url = reverse("analysis_report", args=[subject.pk])
            return redirect(f"{url}?report={report.pk}")
    elif report is None and any(key in request.GET for key, _label in MODULES):
        # 下拉選單一改就用網址帶選擇回來，即時預覽；不會存成歷史紀錄
        form = AnalysisRecordForm(request.GET, subject=subject)
        is_preview = True
    else:
        form = AnalysisRecordForm(subject=subject, selected=selected)

    if report is not None:
        records = report.selected_records
        results = report.module_results
        overall = report.overall_result
    elif form.is_bound and not form.is_valid():
        records = {}
        results = {}
        overall = ""
    else:
        if form.is_bound:
            selected = form.cleaned_data
        else:
            selected = {
                key: form.initial[key] for key, _label in MODULES
            }
        records, results, overall = build_report_data(selected)

    rows = [
        {
            "key": key,
            "label": label,
            "result": results.get(key, {"state": "pending", "reason": "尚未選擇資料"}),
            "record": records.get(key, {}),
            "date_label": (
                timezone.localtime(datetime.fromisoformat(records[key]["date"])).strftime("%Y/%m/%d %H:%M")
                if records.get(key, {}).get("date") else "尚未選擇"
            ),
        }
        for key, label in MODULES
    ]
    selected_dates = [
        datetime.fromisoformat(record["date"])
        for record in records.values()
        if record.get("date")
    ]
    dates_far_apart = (
        len(selected_dates) > 1
        and max(selected_dates) - min(selected_dates) > timedelta(days=30)
    )
    return render(request, "core/analysis_report.html", {
        **workflow_navigation(request, subject),
        "subject": subject,
        "subject_name": get_subject_display_name(subject),
        "contact_line": get_subject_contact_line(subject),
        "form": form,
        "rows": rows,
        "system_rows": results.get("systems", []),
        "overall": overall,
        "yes_count": sum(1 for row in rows if row["result"].get("state") == "yes"),
        "report": report,
        "is_preview": is_preview,
        "reports": reports[:15],
        "can_save": can_save,
        "dates_far_apart": dates_far_apart,
        "has_bfs": form.fields["bfs"].queryset.exists(),
        "has_meridian": form.fields["meridian"].queryset.exists(),
        "bfs_history_url": (
            reverse("bfs_list") + f"?subject={subject.pk}"
            if can_view_all_records(request.user) else reverse("bfs_list")
        ),
        "meridian_history_url": (
            reverse("meridian_list") + f"?subject={subject.pk}"
            if can_view_all_records(request.user) else reverse("meridian_list")
        ),
    })
