from django.conf import settings
from django.shortcuts import render, redirect

from ..forms import BFSTestForm
from ..models import BFSTest, BFSTestFile
from ..services.bfs import analyze_bfs_pdf


LEVEL_NAMES = {1: "活躍", 2: "理想", 3: "暫緩", 4: "減弱", 5: "異常", 6: "嚴重"}

def upload_bfs_test(request):
    if request.method == 'POST':
        form = BFSTestForm(request.POST)
        pdf_files = request.FILES.getlist('pdf_files')

        if form.is_valid() and pdf_files:
            bfs_test = form.save()

            # 分發流水號
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

            return redirect('bfs_detail', pk=bfs_test.pk) # 跳轉至 BFS測試詳細頁面
    else:
        form = BFSTestForm() # 如果是 GET 請求，則建立一個空的表單
    return render(request, "core/upload_bfs_test.html", {'form': form})

def _build_display_rows(analysis_result):
    """
    把 analysis_result 這份原始 JSON 整理成 Template 可以直接
    迴圈渲染的結構，不需要在 Template 裡做字典查找或型別轉換。
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
            levels.append({'name': level_name, 'count': count})
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

def bfs_detail(request, pk):
    bfs_test = BFSTest.objects.prefetch_related('files').get(pk=pk)

    files_display = []
    for bfs_file in bfs_test.files.all():
        files_display.append({
            'file': bfs_file,
            'display': _build_display_rows(bfs_file.analysis_result),
        })

    return render(request, "core/bfs_detail.html", {
        'bfs_test': bfs_test,
        'files_display': files_display,
    })