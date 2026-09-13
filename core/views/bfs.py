from datetime import datetime, time as datetime_time
from urllib.parse import urlencode
from django.templatetags.static import static as static_url

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from ..forms import BFSTestForm, BFSTestUpdateForm
from ..models import BFSTest, BFSTestFile, Questionnaire
from ..services.subjects import get_subject_display_name, get_user_identity_name
from .permissions import (
    can_manage_all_records,
    can_manage_record,
    can_view_all_records,
    get_manageable_record_or_404,
    get_viewable_record_or_404,
    scope_viewable_records,
)


LEVEL_NAMES = {1: "活躍", 2: "理想", 3: "暫緩", 4: "減弱", 5: "異常", 6: "嚴重"}

LEVEL_ICONS = {
    1: "images/bfs_levels/level_1.png",
    2: "images/bfs_levels/level_2.png",
    3: "images/bfs_levels/level_3.png",
    4: "images/bfs_levels/level_4.png",
    5: "images/bfs_levels/level_5.png",
    6: "images/bfs_levels/level_6.png",
}

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
        "form": form,
        "target_subject_user": subject_user,
        "target_subject_name": subject_name,
        "show_upload_target": can_manage_all_records(request.user)
        and subject_user.id != request.user.id,
    }

@login_required(login_url="login")
def bfs_list(request):
    bfs_tests = scope_viewable_records(BFSTest.objects.all(), request.user).prefetch_related('files')
    target_subject = None
    subject_id = request.GET.get("subject")
    upload_url = reverse("upload_bfs_test")

    if subject_id and can_view_all_records(request.user):
        target_subject = get_user_model().objects.filter(pk=subject_id).first()
        if target_subject:
            bfs_tests = bfs_tests.filter(user=target_subject)
            upload_url = (
                f"{upload_url}?"
                f"{urlencode({'subject': target_subject.id, 'patient_name': get_subject_display_name(target_subject)})}"
            )

    for bfs_test in bfs_tests:
        has_file_issue = any(
            f.analysis_status == 'needs_review' for f in bfs_test.files.all()
        )
        bfs_test.has_issue = bfs_test.needs_date_review or has_file_issue
        bfs_test.subject_display_name = (
            get_subject_display_name(bfs_test.user) if bfs_test.user_id else "未指定"
        )

    return render(request, "core/bfs_list.html", {
        "bfs_tests": bfs_tests,
        "target_subject": target_subject,
        "target_subject_name": get_subject_display_name(target_subject)
        if target_subject
        else "",
        "upload_url": upload_url,
        "can_manage_all_records": can_manage_all_records(request.user),
        "can_view_all_records": can_view_all_records(request.user),
    })

def _parse_bfs_date_string(date_str):
    """把 PDF 抓到的日期字串轉成 timezone-aware 的 datetime(時間補 00:00)。"""
    try:
        parsed_date = datetime.strptime(date_str, "%Y/%m/%d").date()
    except (ValueError, TypeError):
        return None
    naive_dt = datetime.combine(parsed_date, datetime_time.min)
    if timezone.is_naive(naive_dt):
        return timezone.make_aware(naive_dt) # 強制幫它貼上 Django 設定的本地時區標籤
    return naive_dt


def _resolve_test_date(per_file_date_detections):
    """
    根據這次上傳的所有 PDF 各自的 date_detection 結果，
    判斷這筆 BFSTest 最終的測試日期，以及要不要標記人工確認。
    """
    ok_dates = {
        d.get("date") for d in per_file_date_detections
        if d.get("status") == "ok"
    }

    if not ok_dates:
        return {"test_date": None, "needs_date_review": True}

    if len(ok_dates) > 1:
        return {"test_date": None, "needs_date_review": True}

    parsed = _parse_bfs_date_string(ok_dates.pop())
    if parsed is None:
        return {"test_date": None, "needs_date_review": True}

    return {"test_date": parsed, "needs_date_review": False}

@login_required(login_url="login")
def upload_bfs_test(request):
    subject_user = _resolve_upload_subject(request)

    if request.method == 'POST':
        form = BFSTestForm(request.POST)
        pdf_files = request.FILES.getlist('pdf_files')

        if form.is_valid() and pdf_files:
            try:
                from ..services.bfs import analyze_bfs_pdf
            except ImportError:
                messages.error(request, "BFS 分析套件尚未安裝，請先執行 pip install -r requirements.txt。")
                return render(
                    request,
                    "core/upload_bfs_test.html",
                    _upload_context(form, request, subject_user),
                )

            # 先給暫時值
            bfs_test = form.save(commit=False)
            bfs_test.user = subject_user
            identity_name = get_user_identity_name(subject_user)
            if identity_name:
                bfs_test.patient_name = identity_name
            if not bfs_test.test_date:
                bfs_test.test_date = timezone.now()
            bfs_test.save()

            date_detections = []
            for index, pdf_file in enumerate(pdf_files, start=1):
                bfs_file = BFSTestFile.objects.create(
                    bfs_test=bfs_test,
                    file_number=index,
                    pdf_file=pdf_file,
                )
                 # 存檔後才有實際路徑，接著馬上自動分析
                result = analyze_bfs_pdf(bfs_file.pdf_file.path)
                bfs_file.detected_template = result['detected_template']
                bfs_file.analysis_status = result['analysis_status']
                bfs_file.analysis_result = result['analysis_result']
                bfs_file.save()

                # 收集每個檔案的日期偵測結果，方便後續彙整
                date_detections.append(
                    result['analysis_result'].get(
                        'date_detection', {"date": None, "status": "not_found"}
                    )
                )

            # 根據每個檔案的日期偵測結果，決定 BFSTest 的最終測試日期
            date_resolution = _resolve_test_date(date_detections)
            if date_resolution['test_date'] is not None:
                bfs_test.test_date = date_resolution['test_date']
            bfs_test.needs_date_review = date_resolution['needs_date_review']
            bfs_test.save()

            return redirect('bfs_detail', pk=bfs_test.pk)
    else:
        initial = {}
        subject_name = request.GET.get("patient_name")
        questionnaire = Questionnaire.objects.filter(user=subject_user).first()
        if subject_name:
            initial["patient_name"] = subject_name
        elif questionnaire:
            initial["patient_name"] = questionnaire.name
        form = BFSTestForm(initial=initial) # 如果是 GET 請求，則建立一個空的表單
    return render(
        request,
        "core/upload_bfs_test.html",
        _upload_context(form, request, subject_user),
    )

def _build_display_rows(analysis_result):
    """
    把 analysis_result 這份原始 JSON 整理成陣列使 Template 可以直接
    迴圈渲染，不需要在 Template 裡做字典查找或型別轉換。
    """
    if not analysis_result or 'color_analysis' not in analysis_result:
        return None

    color = analysis_result['color_analysis']

    captions = analysis_result.get('detection', {}).get('detail', {}).get('captions', {})

    rows = []
    for region in color['regions_present']:
        counts = color['quadrant_counts'][region]
        levels = []
        for level_num, level_name in LEVEL_NAMES.items():
            # JSON 存進資料庫後，數字鍵會變成字串鍵，兩種都嘗試取值
            count = counts.get(str(level_num), counts.get(level_num, 0))
            levels.append({'name': level_name, 'count': count, 'icon_url': static_url(LEVEL_ICONS[level_num]),})
        rows.append({
            'region': region,
            'caption': captions.get(region, region),
            'levels': levels,
            'total': color['quadrant_totals'][region],
        })

    return {
        'rows': rows,
        'total_all': color['total_all'],
        'suspicious_count': len(color.get('suspicious', [])),
    }

# 將多筆資料輸出結果統合成一個陣列送往 templates
@login_required(login_url="login")
def bfs_detail(request, pk):
    bfs_test = get_viewable_record_or_404(
        BFSTest.objects.prefetch_related('files'),
        request.user,
        pk=pk,
    )

    files_display = []
    for bfs_file in bfs_test.files.all():
        files_display.append({
            'file': bfs_file,
            'display': _build_display_rows(bfs_file.analysis_result),
        })

    return render(request, "core/bfs_detail.html", {
        'bfs_test': bfs_test,
        'files_display': files_display,
        'can_view_all_records': can_view_all_records(request.user),
        'can_manage_this_record': can_manage_record(request.user, bfs_test),
    })

# 在前端確認補填遺失的測試日期
@login_required(login_url="login")
def bfs_confirm_date(request, pk):
    bfs_test = get_manageable_record_or_404(BFSTest.objects.all(), request.user, pk=pk)

    if request.method == 'POST':
        new_date = request.POST.get('test_date')
        if new_date:
            bfs_test.test_date = new_date
            bfs_test.needs_date_review = False
            bfs_test.save()
            messages.success(request, "測試日期已更新。")

    return redirect('bfs_detail', pk=bfs_test.pk)

@login_required(login_url="login")
def bfs_update(request, pk):
    bfs_test = get_manageable_record_or_404(BFSTest.objects.all(), request.user, pk=pk)

    if request.method == 'POST':
        form = BFSTestUpdateForm(request.POST, instance=bfs_test)
        if form.is_valid():
            form.save()
            messages.success(request, "測試記錄已更新。")
            return redirect('bfs_detail', pk=bfs_test.pk)
    else:
        form = BFSTestUpdateForm(instance=bfs_test)

    return render(request, "core/bfs_update.html", {
        'form': form,
        'bfs_test': bfs_test,
    })

@login_required(login_url="login")
def bfs_delete(request, pk):
    bfs_test = get_manageable_record_or_404(
        BFSTest.objects.prefetch_related('files'),
        request.user,
        pk=pk,
    )

    if request.method == 'POST':
        for bfs_file in bfs_test.files.all():
            bfs_file.pdf_file.delete(save=False)  # 先刪實體檔案
        bfs_test.delete()  # 再刪資料庫記錄（CASCADE 會連帶清掉 BFSTestFile）
        messages.success(request, "測試記錄已刪除。")
        return redirect('bfs_list')

    return redirect('bfs_detail', pk=bfs_test.pk)
