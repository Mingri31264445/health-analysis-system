import os
import tempfile
from datetime import datetime

from django.contrib import messages
from django.shortcuts import render, redirect
from django.utils import timezone
from pdfplumber.utils.exceptions import PdfminerException

from ..forms import MeridianTestForm
from ..services import parse_meridian_pdf, save_meridian_result


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
            return redirect('home')  # 本輪先導回首頁，等 Detail 頁做完再改成 meridian_detail
    else:
        form = MeridianTestForm()
    return render(request, "core/upload_meridian_result.html", {'form': form})
