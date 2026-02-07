from django.shortcuts import render, redirect, get_object_or_404
from .models import Questionnaire
from .forms import QuestionnaireForm, MeridianTestForm, BFSTestForm, FaceDiagnosisForm

def index(request):
    return render(request, 'core/index.html')

#問卷列表
def questionnaire_list(request):

    questionnaires = Questionnaire.objects.all().order_by('-created_at')
    context = {
        'questionnaires': questionnaires
    }
    return render(request, 'core/questionnaire_list.html', context)

#建立問卷
def questionnaire_create(request):
    if request.method == 'POST':
        form = QuestionnaireForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('questionnaire_list')
    else:
        form = QuestionnaireForm()
    return render(request, 'core/questionnaire_create.html', {'form': form})

#刪除問卷
def questionnaire_delete(request, pk):
    questionnaire = get_object_or_404(Questionnaire, pk=pk)
    questionnaire.delete()
    return redirect('questionnaire_list')


#建立經絡測試
def meridian_create(request):
    if request.method == 'POST':
        form = MeridianTestForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = MeridianTestForm()

    return render(request, 'core/meridian_create.html', {'form': form})

#建立BFS測試
def bfs_create(request):
    if request.method == 'POST':
        form = BFSTestForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = BFSTestForm()
    
    return render(request, 'core/bfs_create.html', {'form': form})

#建立面診測試
def face_diagnosis_create(request):
    """新增面診記錄"""
    if request.method == 'POST':
        form = FaceDiagnosisForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = FaceDiagnosisForm()
    
    return render(request, 'core/face_diagnosis_create.html', {'form': form})