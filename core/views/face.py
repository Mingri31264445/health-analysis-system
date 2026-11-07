import shutil
from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from ..forms import FaceDiagnosisForm, FaceDiagnosisUpdateForm
from ..models import FaceDiagnosis, Questionnaire
from ..services.face import (
    FaceAnalysisError,
    FaceEngineUnavailable,
    analyze_front_image,
    is_available,
)
from ..services.subjects import get_subject_display_name, get_user_identity_name
from .permissions import (
    can_manage_all_records,
    can_view_all_records,
    get_manageable_record_or_404,
    get_viewable_record_or_404,
    scope_viewable_records,
)
from .workflow_navigation import workflow_navigation


# 引擎輸出的類別名稱 → 中文顯示名稱
CLASS_LABELS = {
    "blackhead": "黑頭粉刺",
    "whitehead": "白頭粉刺",
    "papule": "丘疹",
    "pustule": "膿皰",
    "nodule": "結節",
    "cyst": "囊腫",
}

# 原圖欄位對照
ORIGINAL_KINDS = {
    "front": "front_image",
    "right": "right_image",
    "left": "left_image",
}


def _result_dir(pk):
    """分析結果圖放在 MEDIA_ROOT/face_diagnosis/results/<pk>/"""
    return Path(settings.MEDIA_ROOT) / "face_diagnosis" / "results" / str(pk)


def _resolve_upload_subject(request):
    subject_id = request.POST.get("subject") or request.GET.get("subject")
    if subject_id and can_manage_all_records(request.user):
        subject_user = get_user_model().objects.filter(pk=subject_id).first()
        if subject_user:
            return subject_user
    return request.user


def _upload_context(form, request, subject_user):
    questionnaire = Questionnaire.objects.filter(user=subject_user).first()
    subject_name = request.GET.get("patient_name") or (
        questionnaire.name if questionnaire else get_subject_display_name(subject_user)
    )
    return {
        **workflow_navigation(request, subject_user, "face"),
        "form": form,
        "target_subject_user": subject_user,
        "target_subject_name": subject_name,
        "show_upload_target": can_manage_all_records(request.user)
        and subject_user.id != request.user.id,
        "engine_available": is_available(),
    }


@login_required(login_url="login")
def upload_face_diagnosis(request):
    subject_user = _resolve_upload_subject(request)

    if request.method == "POST":
        form = FaceDiagnosisForm(request.POST, request.FILES)

        # 引擎沒裝好就不要存任何東西，避免產生沒有分析結果的資料
        if not is_available():
            messages.error(request, "面診分析功能目前未啟用，請聯絡系統管理員。")
            return render(
                request,
                "core/upload_face_diagnosis.html",
                _upload_context(form, request, subject_user),
            )

        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = subject_user
            instance.patient_name = (
                get_user_identity_name(subject_user)
                or get_subject_display_name(subject_user)
            )
            instance.diagnosis_date = timezone.now()
            instance.save()  # 先存原圖，才有檔案路徑和 pk 可以交給引擎

            result_dir = _result_dir(instance.pk)
            result_dir.mkdir(parents=True, exist_ok=True)
            try:
                report = analyze_front_image(instance.front_image.path, result_dir)
                instance.analysis_report = report
                instance.analysis_status = FaceDiagnosis.STATUS_DONE
                instance.analysis_error = ""
            except (FaceAnalysisError, FaceEngineUnavailable) as exc:
                # 這兩種例外的訊息直接給使用者看 FaceAnalysisError:逾時、照片偵測不到人臉、FaceEngineUnavailable:路徑設定錯、face 環境沒裝好
                instance.analysis_status = FaceDiagnosis.STATUS_FAILED
                instance.analysis_error = str(exc)
                messages.error(request, f"面診分析失敗：{exc}")
            instance.analyzed_at = timezone.now()
            instance.save()
            return redirect("face_detail", pk=instance.pk)
    else:
        form = FaceDiagnosisForm()

    return render(
        request,
        "core/upload_face_diagnosis.html",
        _upload_context(form, request, subject_user),
    )

@login_required(login_url="login")
def face_list(request):
    records = scope_viewable_records(FaceDiagnosis.objects.all(), request.user)
    target_subject = None
    subject_id = request.GET.get("subject")
    upload_url = reverse("upload_face_diagnosis")

    if subject_id and can_view_all_records(request.user):
        target_subject = get_user_model().objects.filter(pk=subject_id).first()
        if target_subject:
            records = records.filter(user=target_subject)
            upload_url = (
                f"{upload_url}?"
                f"{urlencode({'subject': target_subject.id, 'patient_name': get_subject_display_name(target_subject)})}"
            )

    records = list(records)
    for record in records:
        record.subject_display_name = (
            get_subject_display_name(record.user) if record.user_id else "未指定"
        )

    return render(request, "core/face_list.html", {
        **workflow_navigation(request, target_subject, "face"),
        "records": records,
        "target_subject": target_subject,
        "target_subject_name": get_subject_display_name(target_subject)
        if target_subject
        else "",
        "upload_url": upload_url,
        "can_manage_all_records": can_manage_all_records(request.user),
        "can_view_all_records": can_view_all_records(request.user),
    })


@login_required(login_url="login")
def face_detail(request, pk):
    record = get_viewable_record_or_404(FaceDiagnosis.objects.all(), request.user, pk=pk)
    report = record.analysis_report or {}

    # 各類別數量，轉成中文標籤，數量多的排前面
    class_counts = [
        {"label": CLASS_LABELS.get(name, name), "count": count}
        for name, count in sorted(
            (report.get("class_counts") or {}).items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    return render(request, "core/face_detail.html", {
        **workflow_navigation(request, record.user, "face"),
        "record": record,
        "report": report,
        "class_counts": class_counts,
        "result_images": report.get("images") or {},
        "can_manage": can_manage_all_records(request.user)
        or record.user_id == request.user.id,
        "can_view_all_records": can_view_all_records(request.user),
    })


@login_required(login_url="login")
def face_update(request, pk):
    record = get_manageable_record_or_404(FaceDiagnosis.objects.all(), request.user, pk=pk)

    if request.method == "POST":
        form = FaceDiagnosisUpdateForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "備註已更新。")
            return redirect("face_detail", pk=record.pk)
    else:
        form = FaceDiagnosisUpdateForm(instance=record)

    return render(request, "core/face_update.html", {
        **workflow_navigation(request, record.user, "face"),
        "form": form,
        "record": record,
    })


@login_required(login_url="login")
def face_delete(request, pk):
    record = get_manageable_record_or_404(FaceDiagnosis.objects.all(), request.user, pk=pk)

    if request.method == "POST":
        list_url = workflow_navigation(request, record.user, "face")["record_list_url"]
        # 先刪三張原圖與分析結果資料夾，再刪資料庫記錄
        record.front_image.delete(save=False)
        record.right_image.delete(save=False)
        record.left_image.delete(save=False)
        shutil.rmtree(_result_dir(record.pk), ignore_errors=True)
        record.delete()
        messages.success(request, "面診記錄已刪除。")
        return redirect(list_url)

    return redirect("face_detail", pk=record.pk)

@login_required(login_url="login")
def face_file_view(request, pk, kind):
    """提供面診圖片:原圖(front/right/left)或分析結果圖(report 內登記的名稱)。
    先做權限檢查，不開放 /media/ 直連。"""
    record = get_viewable_record_or_404(FaceDiagnosis.objects.all(), request.user, pk=pk)

    if kind in ORIGINAL_KINDS:
        field = getattr(record, ORIGINAL_KINDS[kind])
        if not field:
            raise Http404
        return FileResponse(field.open("rb"))

    # 分析結果圖：檔名必須是 analysis_report 裡登記過的，不接受任意路徑
    filename = ((record.analysis_report or {}).get("images") or {}).get(kind)
    if not filename:
        raise Http404
    path = _result_dir(record.pk) / Path(filename).name  # .name 擋掉 ../ 之類的路徑
    if not path.is_file():
        raise Http404
    return FileResponse(open(path, "rb"), content_type="image/png")