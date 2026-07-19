from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from ..forms import QuestionnaireForm
from ..models import Questionnaire
from .auth import safe_next_url, questionnaire_start_url

FEATURES = {
    "face": {
        "label": "面診影像觀察",
        "eyebrow": "FACE IMAGE",
        "action": "查看紀錄",
        "description": "上傳或拍攝臉部影像，作為後續視覺化觀察與健康狀態參考。",
    },
    "bfs": {
        "label": "BFS量測結果",
        "eyebrow": "BFS DATA",
        "action": "查看紀錄",
        "description": "整理 BFS（生物頻譜回饋分析儀）量測資料，建立個人生理狀態的參考分析頁面。",
    },
    "meridian": {
        "label": "經絡檢測分析",
        "eyebrow": "MERIDIAN",
        "action": "查看紀錄",
        "description": "整合經絡檢測資訊，呈現更完整的健康評估概念。",
    },
}

FEATURE_REDIRECTS = {
    "bfs": "bfs_list",
}

@login_required(login_url="login")
def start_analysis_view(request):
    questionnaire = Questionnaire.objects.filter(user=request.user).first()
    if questionnaire is None:
        messages.info(request, "開始分析前，請先完成健康問卷。")
        return redirect(questionnaire_start_url())

    modules = [
        {
            "eyebrow": "QUESTIONNAIRE",
            "label": "健康問卷",
            "description": "更新個人資料、病史與生活習慣，讓後續分析維持最新狀態。",
            "action": "更新問卷",
            "url": reverse("questionnaire") + f"?next={reverse('start_analysis')}",
        },
        {
            "eyebrow": FEATURES["face"]["eyebrow"],
            "label": FEATURES["face"]["label"],
            "description": FEATURES["face"]["description"],
            "action": FEATURES["face"]["action"],
            "url": reverse("feature_gate", args=["face"]),
        },
        {
            "eyebrow": FEATURES["bfs"]["eyebrow"],
            "label": FEATURES["bfs"]["label"],
            "description": FEATURES["bfs"]["description"],
            "action": FEATURES["bfs"]["action"],
            "url": reverse("upload_bfs_test"),
        },
        {
            "eyebrow": FEATURES["meridian"]["eyebrow"],
            "label": FEATURES["meridian"]["label"],
            "description": FEATURES["meridian"]["description"],
            "action": FEATURES["meridian"]["action"],
            "url": reverse("upload_meridian_result"),
        },
    ]

    return render(
        request,
        "core/analysis_start.html",
        {
            "questionnaire": questionnaire,
            "modules": modules,
        },
    )


@login_required(login_url="login")
def questionnaire_view(request):
    instance = Questionnaire.objects.filter(user=request.user).first()
    next_url = safe_next_url(request, reverse("start_analysis"))

    if request.method == "POST":
        form = QuestionnaireForm(request.POST, instance=instance)
        if form.is_valid():
            questionnaire = form.save(commit=False)
            questionnaire.user = request.user
            questionnaire.save()
            messages.success(request, "健康問卷已儲存。")
            return redirect(next_url)
    else:
        form = QuestionnaireForm(instance=instance)

    return render(
        request,
        "core/questionnaire_form.html",
        {
            "form": form,
            "form_sections": form.get_sections(),
            "has_existing": instance is not None,
            "next_url": request.GET.get("next", ""),
        },
    )


@login_required(login_url="login")
def feature_gate(request, feature_key):
    feature = FEATURES.get(feature_key)
    if feature is None:
        return redirect("home")

    has_questionnaire = Questionnaire.objects.filter(user=request.user).exists()
    if not has_questionnaire:
        questionnaire_url = f"{reverse('questionnaire')}?next={request.path}"
        messages.info(request, "請先完成健康問卷，再進入分析功能。")
        return redirect(questionnaire_url)
    
    if feature_key in FEATURE_REDIRECTS:
        return redirect(FEATURE_REDIRECTS[feature_key])

    if feature_key == "bfs":
        return redirect("upload_bfs_test")

    if feature_key == "meridian":
        return redirect("upload_meridian_result")

    return render(request, "core/feature_page.html", {"feature": feature, "feature_key": feature_key})
