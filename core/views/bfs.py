from django.conf import settings
from django.shortcuts import render, redirect

from ..forms import BFSTestForm
from ..models import BFSTest, BFSTestFile
from ..services.bfs import analyze_bfs_pdf


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


def bfs_detail(request, pk):
    bfs_test = BFSTest.objects.prefetch_related('files').get(pk=pk)
    return render(request, "core/bfs_detail.html", {'bfs_test': bfs_test})