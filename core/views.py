from django.shortcuts import render, redirect
from .forms import MeridianTestForm
from .services import parse_meridian_pdf, save_meridian_result

def home(request):
    return render(request, "core/index.html")

def upload_meridian_result(request):
    if request.method == 'POST':
        form = MeridianTestForm(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save()  # 先儲存基本資料和PDF檔案
            # 解析PDF並儲存讀數
            data = parse_meridian_pdf(instance.result_pdf.path)
            save_meridian_result(instance, data)
            return redirect('home')
    else:
        form = MeridianTestForm()
    return render(request, "core/upload_meridian_result.html", {'form': form})