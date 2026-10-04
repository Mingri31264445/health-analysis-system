import os
import tempfile
from datetime import datetime
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import FileResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
try:
    from pdfplumber.utils.exceptions import PdfminerException
except ImportError:
    class PdfminerException(Exception):
        pass

from ..forms import MeridianTestForm, MeridianTestUpdateForm
from ..models import MeridianTest, Questionnaire
from ..services.subjects import get_subject_display_name, get_user_identity_name
from .permissions import (
    can_manage_all_records,
    can_manage_record,
    can_view_all_records,
    get_manageable_record_or_404,
    get_viewable_record_or_404,
    scope_viewable_records,
)


MERIDIANS_ORDER = ['肺經', '心包', '心經', '小腸', '三焦', '大腸', '脾經', '肝經', '腎經', '膀胱', '膽經', '胃經']
MIN_TREND_COMPARE = 2
MAX_TREND_COMPARE = 4

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


def _parse_measure_datetime(raw):
    """把 PDF 的 '2025/7/25 下午 03:26:04' 轉成 timezone-aware datetime。
    先把中文上午/下午轉成 AM/PM，交給 strptime 的 %p 處理 12 小時制
    （含 12 點邊界：下午12→12:00、上午12→00:00，不需手動 +12）。
    格式不符會拋 ValueError，由呼叫端的 except 視同 PDF 內容異常處理。"""
    normalized = raw.replace('上午', 'AM').replace('下午', 'PM')
    naive = datetime.strptime(normalized, '%Y/%m/%d %p %I:%M:%S')
    return timezone.make_aware(naive)

@login_required(login_url="login")
def upload_meridian_result(request):
    subject_user = _resolve_upload_subject(request)

    if request.method == 'POST':
        form = MeridianTestForm(request.POST, request.FILES)
        if form.is_valid():
            pdf_file = form.cleaned_data['result_pdf']

            # 上傳檔先寫到暫存位置才能交給 parser（FILES 可能是 in-memory/temp）
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                for chunk in pdf_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            try:
                from ..services import parse_meridian_pdf, save_meridian_result

                data = parse_meridian_pdf(tmp_path)
                # PDF 的測量日期含日期+12小時制時間（如 '2025/7/25 下午 03:26:04'），
                # 轉成 timezone-aware datetime 才能存進 DateTimeField；
                # 轉換失敗(ValueError)視同 PDF 內容異常，走同一句錯誤訊息。
                test_date = _parse_measure_datetime(data['測量日期'])
            except ImportError:
                messages.error(request, "經絡 PDF 分析套件尚未安裝，請先執行 pip install -r requirements.txt。")
                return render(
                    request,
                    "core/upload_meridian_result.html",
                    _upload_context(form, request, subject_user),
                )
            except (PdfminerException, IndexError, AttributeError, ValueError, FileNotFoundError):
                messages.error(request, "這份 PDF 無法解析，請確認是經絡儀原始報告。")
                return render(
                    request,
                    "core/upload_meridian_result.html",
                    _upload_context(form, request, subject_user),
                )
            finally:
                os.unlink(tmp_path)  # 不論成敗都清掉暫存檔

            # 解析＋日期轉換都成功，這時候才真正建立記錄（避免孤兒資料）
            instance = form.save(commit=False)
            instance.user = subject_user
            instance.patient_name = get_user_identity_name(subject_user) or data['姓名']
            instance.test_date = test_date
            instance.gender = data['性別']
            instance.birth_date = data['生日']
            instance.age = data['年齡']
            instance.save()  # 這時候才真正存 PDF 檔案本身

            save_meridian_result(instance, data)
            return redirect('meridian_detail', pk=instance.pk)
    else:
        form = MeridianTestForm()
    return render(
        request,
        "core/upload_meridian_result.html",
        _upload_context(form, request, subject_user),
    )


def _classify_reading(value, thresholds):
    """依門檻值把單一數值分成三色：
    'danger'（過高/過低）/ 'warn'（偏高/偏低）/ 'good'（正常）。
    門檻值理論上 parse 成功一定有；但因欄位是 null=True，任一為 None（或值為 None）
    時回傳 'unknown' 不做比較，避免 None > value 直接讓程式炸掉。"""
    too_high = thresholds['toohigh']
    high = thresholds['high']
    low = thresholds['low']
    too_low = thresholds['toolow']

    if value is None or None in (too_high, high, low, too_low):
        return 'unknown'

    if value > too_high or value < too_low:
        return 'danger'
    if value > high or value < low:
        return 'warn'
    return 'good'

@login_required(login_url="login")
def meridian_list(request):
    meridian_tests = scope_viewable_records(MeridianTest.objects.all(), request.user)
    target_subject = None
    subject_id = request.GET.get("subject")
    upload_url = reverse("upload_meridian_result")

    if subject_id and can_view_all_records(request.user):
        target_subject = get_user_model().objects.filter(pk=subject_id).first()
        if target_subject:
            meridian_tests = meridian_tests.filter(user=target_subject)
            upload_url = (
                f"{upload_url}?"
                f"{urlencode({'subject': target_subject.id, 'patient_name': get_subject_display_name(target_subject)})}"
            )

    for meridian_test in meridian_tests:
        meridian_test.subject_display_name = (
            get_subject_display_name(meridian_test.user)
            if meridian_test.user_id
            else "未指定"
        )

    return render(request, "core/meridian_list.html", {
        "meridian_tests": meridian_tests,
        "target_subject": target_subject,
        "target_subject_name": get_subject_display_name(target_subject)
        if target_subject
        else "",
        "upload_url": upload_url,
        "can_manage_all_records": can_manage_all_records(request.user),
        "can_view_all_records": can_view_all_records(request.user),
    })


@login_required(login_url="login")
def meridian_detail(request, pk):
    test = get_viewable_record_or_404(
        MeridianTest.objects.prefetch_related('readings'),
        request.user,
        pk=pk,
    )
    readings_by_name = {r.meridian: r for r in test.readings.all()}

    thresholds = {
        'toohigh': test.threshold_toohigh,
        'high': test.threshold_high,
        'low': test.threshold_low,
        'toolow': test.threshold_toolow,
    }

    rows = []
    for name in MERIDIANS_ORDER:
        reading = readings_by_name.get(name)
        if reading is None:
            continue  # 防呆：理論上一定有 12 條，但避免資料不齊全時直接炸掉
        rows.append({
            'name': name,
            'left_org': {'value': reading.left_org, 'level': _classify_reading(reading.left_org, thresholds)},
            'left_cmp': {'value': reading.left_cmp, 'level': _classify_reading(reading.left_cmp, thresholds)},
            'right_org': {'value': reading.right_org, 'level': _classify_reading(reading.right_org, thresholds)},
            'right_cmp': {'value': reading.right_cmp, 'level': _classify_reading(reading.right_cmp, thresholds)},
        })

    return render(request, "core/meridian_detail.html", {
        'test': test,
        'rows': rows,
        'can_view_all_records': can_view_all_records(request.user),
        'can_manage_this_record': can_manage_record(request.user, test),
    })

@login_required(login_url="login")
def meridian_file_view(request, pk):
    test = get_viewable_record_or_404(
        MeridianTest.objects.all(),
        request.user,
        pk=pk,
    )
    return FileResponse(test.result_pdf.open('rb'), content_type='application/pdf')

def _build_meridian_trend(tests):
    """將要比較的幾筆經絡測試整理成折線圖用的資料。
    X 軸共 25 格：左側 12 條經絡 + 1 格空白（值為 None,折線在這裡斷開、
    之後分隔線也畫在這裡）+ 右側 12 條經絡。Y 值用補償值(cmp)"""
    series = []
    for t in tests:
        # 將這筆測試的所有經絡數據整理成dict字典，以經絡名稱為key
        readings = {r.meridian: r for r in t.readings.all()}
        # 該經絡如果沒有量測資料， readings.get(name) 找不到時會回傳 None，getattr 會回傳預設值 None
        left = [getattr(readings.get(name), 'left_cmp', None) for name in MERIDIANS_ORDER]
        right = [getattr(readings.get(name), 'right_cmp', None) for name in MERIDIANS_ORDER]
        # 組合成折線圖所需的資料格式
        series.append({
            'test_id': t.pk,
            'label': timezone.localtime(t.test_date).strftime('%Y/%m/%d %H:%M'),
            'values': left + [None] + right,
        })
    return {
        'meridians': MERIDIANS_ORDER,# 經絡名稱順序
        'series': series,# 每筆測試的折線圖資料
    }


@login_required(login_url="login")
def meridian_trend(request):
    # 從 GET 參數取得要比較的測試記錄 id
    raw_ids = request.GET.get('ids', '')
    try:
        # dict.fromkeys 用來去除重複 id 並保留使用者選取順序
        ids = list(dict.fromkeys(int(x) for x in raw_ids.split(',') if x.strip()))
    except ValueError:
        return HttpResponseBadRequest("ids 格式錯誤")

    if not (MIN_TREND_COMPARE <= len(ids) <= MAX_TREND_COMPARE):
        return HttpResponseBadRequest(
            f"請選擇 {MIN_TREND_COMPARE}～{MAX_TREND_COMPARE} 筆測試記錄"
        )

    # 每一筆都走原本的權限檢查：沒有權限或不存在會直接 404
    tests = [
        get_viewable_record_or_404(
            MeridianTest.objects.prefetch_related('readings'),
            request.user,
            pk=pk,
        )
        for pk in ids
    ]

    # 管理員看得到全部人的紀錄，這裡限制只能比較同一位受測者
    if len({t.user_id for t in tests}) > 1:
        return HttpResponseBadRequest("只能比較同一位受測者的紀錄")

    # 依測試日期排序，讓折線圖的顯示順序符合時間軸
    tests.sort(key=lambda t: t.test_date)
    return JsonResponse(
        _build_meridian_trend(tests),
        json_dumps_params={'ensure_ascii': False}, # 讓中文經絡名稱不被轉成unicode 亂碼
    )

@login_required(login_url="login")
def meridian_update(request, pk):
    test = get_manageable_record_or_404(MeridianTest.objects.all(), request.user, pk=pk)

    if request.method == 'POST':
        form = MeridianTestUpdateForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, "備註已更新。")
            return redirect('meridian_detail', pk=test.pk)
    else:
        form = MeridianTestUpdateForm(instance=test)

    return render(request, "core/meridian_update.html", {
        'form': form,
        'test': test,
    })

@login_required(login_url="login")
def meridian_delete(request, pk):
    test = get_manageable_record_or_404(MeridianTest.objects.all(), request.user, pk=pk)

    if request.method == 'POST':
        test.result_pdf.delete(save=False)  # 先刪實體 PDF
        test.delete()  # 再刪資料庫記錄（CASCADE 會連帶清掉 12 條 MeridianReading）
        messages.success(request, "測試記錄已刪除。")
        return redirect('meridian_list')

    return redirect('meridian_detail', pk=test.pk)
