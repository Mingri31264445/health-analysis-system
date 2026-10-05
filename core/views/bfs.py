from datetime import datetime, time as datetime_time
from urllib.parse import urlencode
from django.templatetags.static import static as static_url

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import FileResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
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

# 平均等級的權重：等級數字越大代表狀態越差
LEVEL_WEIGHTS = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}
MIN_TREND_COMPARE = 2
MAX_TREND_COMPARE = 4
TREND_STABLE_THRESHOLD = 0.05  # 前後差距不超過這個值視為持平

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
        total = color['quadrant_totals'][region]
        levels = []
        for level_num, level_name in LEVEL_NAMES.items():
            # JSON 存進資料庫後，數字鍵會變成字串鍵，兩種都嘗試取值
            count = counts.get(str(level_num), counts.get(level_num, 0))
            percentage = (count / total * 100) if total else 0 #排除 total 為 0 的情況，避免除以零爆開
            levels.append({
                'name': level_name,
                'count': count,
                'icon_url': static_url(LEVEL_ICONS[level_num]),
                'percentage': percentage,
            })
        rows.append({
            'region': region,
            'caption': captions.get(region, region),
            'levels': levels,
            'total': total,
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

@login_required(login_url="login")
def bfs_file_view(request, pk, file_number):
    bfs_test = get_viewable_record_or_404(
        BFSTest.objects.prefetch_related('files'),
        request.user,
        pk=pk,
    )
    bfs_file = get_object_or_404(bfs_test.files, file_number = file_number)
    return FileResponse(bfs_file.pdf_file.open('rb'), content_type='application/pdf')

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

def _weighted_sum(counts):
    """Σ(等級權重 * 該等級點數) JSON 存進資料庫後數字鍵會變字串"""
    return sum(
        weight * counts.get(str(level), counts.get(level, 0)) # 各等級的點數(count)乘上權重
        for level, weight in LEVEL_WEIGHTS.items() # comprehension / generator expression 括號是必要的
    )


def _make_trend_row(label, caption, values, is_overall=False):
    """對照表的一列。變化 = 最新 - 最早；並判斷這一列的趨勢是變好、變差還是持平"""
    first, last = values[0], values[-1] # 取第一筆(values[0])與最後一筆(values[-1])的值
    diff = round(last - first, 2) if first is not None and last is not None else None # 都有值才計算差距，否則 diff = None 四捨五入到小數點第二位才不會噴錯
    if diff is None:
        trend = None
    elif diff > TREND_STABLE_THRESHOLD:
        trend = 'worse'
    elif diff < -TREND_STABLE_THRESHOLD:
        trend = 'better'
    else:
        trend = 'same'
    # 把這一列的資訊整理成 dict 回傳給前端
    return {
        'label': label,
        'caption': caption,
        'values': values,
        'diff': diff,
        'trend': trend,
        'is_overall': is_overall,
    }


def _trend_labels(tests):
    """如果同一天有多筆測試，則在日期後加上 (1)、(2)… 區別"""
    labels = [timezone.localtime(t.test_date).strftime('%Y/%m/%d') for t in tests] # 把時間轉成本地時區，然後格式化成 YYYY/MM/DD 字串
    # ['2026/09/01 (1)', '2026/09/01 (2)', '2026/09/08']
    return [
        f"{label} ({i + 1})" if labels.count(label) > 1 else label # 判斷同一個日期出現第二次以上
        for i, label in enumerate(labels) # enumerate() 會把 labels 變成 (index, value) 的 tuple，i 是 index，label 是 value
    ]


def _build_bfs_trend(tests, labels):
    """tests 需已依 test_date 由舊到新排序。
    依 detected_template(bfs1、bfs2…)分組，每組一張圖；
    同一組內用部位key對齊不同次測試,某次沒有的部位值為 None(折線會斷開)。"""
    groups = {}
    # 第幾次測試 = idx，測試本身 = test
    for idx, test in enumerate(tests):
        # 這次檢測底下的第幾份檔案 = bfs_file，檔案的分析結果 = result，檔案偵測到的版型 = template
        for bfs_file in test.files.all():
            result = bfs_file.analysis_result
            template = bfs_file.detected_template
            # 跳過沒用的檔案
            if not template or not result or 'color_analysis' not in result:
                continue
            color = result['color_analysis']
            captions = result.get('detection', {}).get('detail', {}).get('captions', {})
            group = groups.setdefault(template, {'regions': {}, 'scores': {}}) # setdefault() 會回傳指定 key 的 value，如果沒有就建立一個新的 dict
            if idx in group['scores']:
                continue  # 同一次測試出現兩份相同版型時，以第一份為準
            scores = group['scores'][idx] = {} # 連續建立 group['scores'][idx] 為空 dict，方便後續存放各部位的分數
            for region in color['regions_present']:
                counts = color['quadrant_counts'][region] # 各等級的點數
                total = color['quadrant_totals'][region] # 該部位的總點數
                group['regions'].setdefault(region, captions.get(region, region))
                weighted = _weighted_sum(counts) # 該部位的加權和
                scores[region] = round(weighted / total, 2) if total else None # 避免除以零

    charts = []
    for template in sorted(groups):
        group = groups[template]
        if len(group['scores']) < 2:
            continue  # 只有一次測試有這個版型，沒有趨勢可比
        # 所有測試都沒有點數的部位（例如空象限）不顯示
        region_keys = [
            k for k in group['regions']
            if any(group['scores'].get(idx, {}).get(k) is not None for idx in range(len(tests)))
        ]
        captions = [group['regions'][k] for k in region_keys]
        series = []
        for idx, test in enumerate(tests):
            scores = group['scores'].get(idx, {}) # 如果這次測試沒有這個版型，則回傳空 dict
            series.append({
                'test_id': test.pk,
                'label': labels[idx],
                'values': [scores.get(k) for k in region_keys], # 沒有這個部位就是 None
            })
        # series 是每次檢測一列，對照表要的是每個部位一列，所以要把表格轉 90 度
        rows = [
            _make_trend_row(str(i + 1), caption, [s['values'][i] for s in series]) # 將每個部位丟給 _make_trend_row() 去計算 diff
            for i, caption in enumerate(captions)
        ]
        charts.append({'template': template, 'captions': captions, 'series': series, 'rows': rows})
    return charts

def _build_bfs_overall(tests, labels):
    """整份報告的平均等級：把該次測試所有檔案、所有部位的點數合併後計算。
    同時回傳涵蓋的檔案數與總點數，方便看出各次測試涵蓋範圍是否一致。"""
    overall = []
    for test, label in zip(tests, labels):
        weighted_total = 0
        point_total = 0
        file_count = 0
        seen_templates = set()
        for bfs_file in test.files.all():
            result = bfs_file.analysis_result
            template = bfs_file.detected_template
            if not template or not result or 'color_analysis' not in result:
                continue
            if template in seen_templates:
                continue  # 與趨勢圖一致：同一次測試出現兩份相同版型時，以第一份為準
            seen_templates.add(template)
            color = result['color_analysis']
            for region in color['regions_present']:
                weighted_total += _weighted_sum(color['quadrant_counts'][region])
                point_total += color['quadrant_totals'][region]
            file_count += 1
        overall.append({
            'label': label,
            'average': round(weighted_total / point_total, 2) if point_total else None,
            'file_count': file_count,
            'point_total': point_total,
        })
    return overall

@login_required(login_url="login")
def bfs_trend(request):
    raw_ids = request.GET.get('ids', '')
    try:
        ids = list(dict.fromkeys(int(x) for x in raw_ids.split(',') if x.strip()))  # 去除重複 [12, 15, 20]
    except ValueError:
        return HttpResponseBadRequest("ids 格式錯誤") # ?ids=1,abc

    if not (MIN_TREND_COMPARE <= len(ids) <= MAX_TREND_COMPARE):
        return HttpResponseBadRequest(
            f"請選擇 {MIN_TREND_COMPARE}～{MAX_TREND_COMPARE} 筆測試記錄"
        )

    # 每一筆都走原本的權限檢查：沒有權限或不存在會直接 404
    # 避免有人用亂猜 id 的方式探測資料
    tests = [
        get_viewable_record_or_404(
            BFSTest.objects.prefetch_related('files'),
            request.user,
            pk=pk,
        )
        for pk in ids
    ]

    if len({t.user_id for t in tests}) > 1:
        return HttpResponseBadRequest("只能比較同一位受測者的紀錄")

    tests.sort(key=lambda t: t.test_date)
    labels = _trend_labels(tests)
    charts = _build_bfs_trend(tests, labels)
    overall = _build_bfs_overall(tests, labels)
    return render(request, "core/bfs_trend.html", {
        'patient_name': tests[-1].patient_name,
        'labels': labels,
        'charts': charts,
        # 整份報告平均
        'overall': overall,
        'overall_trend': _make_trend_row(
            '', '整份報告平均', [o['average'] for o in overall], is_overall=True,
        ),
        # 各次測試涵蓋的檔案數不同時，提醒使用者解讀時要留意
        'coverage_differs': len({o['file_count'] for o in overall}) > 1,
        # 給圖表用的精簡資料（對照表用的 rows 不需要送進 JS）
        'chart_data': [
            {'template': c['template'], 'captions': c['captions'], 'series': c['series']}
            for c in charts
        ],
    })