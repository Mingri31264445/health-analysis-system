import os
import tempfile
from datetime import datetime

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from pdfplumber.utils.exceptions import PdfminerException

from ..forms import MeridianTestForm
from ..models import MeridianTest
from ..services import parse_meridian_pdf, save_meridian_result


MERIDIANS_ORDER = ['肺經', '心包', '心經', '小腸', '三焦', '大腸', '脾經', '肝經', '腎經', '膀胱', '膽經', '胃經']


def _parse_measure_datetime(raw):
    """把 PDF 的 '2025/7/25 下午 03:26:04' 轉成 timezone-aware datetime。
    先把中文上午/下午轉成 AM/PM，交給 strptime 的 %p 處理 12 小時制
    （含 12 點邊界：下午12→12:00、上午12→00:00，不需手動 +12）。
    格式不符會拋 ValueError，由呼叫端的 except 視同 PDF 內容異常處理。"""
    normalized = raw.replace('上午', 'AM').replace('下午', 'PM')
    naive = datetime.strptime(normalized, '%Y/%m/%d %p %I:%M:%S')
    return timezone.make_aware(naive)


def upload_meridian_result(request):
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
                data = parse_meridian_pdf(tmp_path)
                # PDF 的測量日期含日期+12小時制時間（如 '2025/7/25 下午 03:26:04'），
                # 轉成 timezone-aware datetime 才能存進 DateTimeField；
                # 轉換失敗(ValueError)視同 PDF 內容異常，走同一句錯誤訊息。
                test_date = _parse_measure_datetime(data['測量日期'])
            except (PdfminerException, IndexError, AttributeError, ValueError, FileNotFoundError):
                messages.error(request, "這份 PDF 無法解析，請確認是經絡儀原始報告。")
                return render(request, "core/upload_meridian_result.html", {'form': form})
            finally:
                os.unlink(tmp_path)  # 不論成敗都清掉暫存檔

            # 解析＋日期轉換都成功，這時候才真正建立記錄（避免孤兒資料）
            instance = form.save(commit=False)
            instance.patient_name = data['姓名']
            instance.test_date = test_date
            instance.gender = data['性別']
            instance.birth_date = data['生日']
            instance.age = data['年齡']
            instance.save()  # 這時候才真正存 PDF 檔案本身

            save_meridian_result(instance, data)
            return redirect('meridian_detail', pk=instance.pk)
    else:
        form = MeridianTestForm()
    return render(request, "core/upload_meridian_result.html", {'form': form})


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


def meridian_list(request):
    meridian_tests = MeridianTest.objects.all()
    return render(request, "core/meridian_list.html", {"meridian_tests": meridian_tests})


def meridian_detail(request, pk):
    test = get_object_or_404(MeridianTest, pk=pk)
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
    })
