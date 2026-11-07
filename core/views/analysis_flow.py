from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse

from ..forms import QuestionnaireForm
from ..models import BFSTest, FaceDiagnosis, MeridianTest, Questionnaire
from .auth import safe_next_url, questionnaire_start_url

FEATURES = {
    "face": {
        "label": "面診影像觀察",
        "eyebrow": "FACE IMAGE",
        "action": "查看紀錄",
        "description": "以同一位受測者為核心，保存不同時間的臉部影像紀錄，作為長期追蹤與健康狀態觀察參考。",
        "focus": "面診影像不只是單張照片辨識，後續會以拍攝一致性、跨時間比較與隱私控管作為設計重點。",
        "considerations": [
            {
                "label": "拍攝一致性",
                "description": "規劃正面、左側、右側影像與拍攝引導，降低角度、距離與光線差異造成的誤判。",
            },
            {
                "label": "長期追蹤",
                "description": "同一受測者可累積多筆面診紀錄，後續可比較不同日期的狀態變化。",
            },
            {
                "label": "資料整合",
                "description": "健康問卷、BFS 與經絡儀資料作為背景脈絡，協助後續綜合呈現。",
            },
            {
                "label": "隱私控管",
                "description": "臉部影像屬於敏感資料，需透過登入、角色權限與資料最小化降低風險。",
            },
        ],
    },
    "bfs": {
        "label": "BFS量測結果",
        "eyebrow": "BFS DATA",
        "action": "查看紀錄",
        "description": "整理 BFS（生物頻譜回饋分析儀）量測資料，建立個人生理狀態的參考分析頁面。",
        "focus": "BFS 可作為同一受測者的多次量測紀錄，重點在於歷史資料管理與變化追蹤。",
    },
    "meridian": {
        "label": "經絡檢測分析",
        "eyebrow": "MERIDIAN",
        "action": "查看紀錄",
        "description": "整合經絡檢測資訊，呈現更完整的健康評估概念。",
        "focus": "經絡儀資料會與受測者帳號綁定，後續可和問卷、BFS 與面診紀錄一起查看。",
    },
}

FEATURE_REDIRECTS = {
    "face": "face_list",
    "bfs": "bfs_list",
    "meridian": "meridian_list",
}

@login_required(login_url="login")
def start_analysis_view(request):
    questionnaire = Questionnaire.objects.filter(user=request.user).first()
    if questionnaire is None:
        messages.info(request, "開始分析前，請先完成健康問卷。")
        return redirect(questionnaire_start_url())

    face_records = FaceDiagnosis.objects.filter(user=request.user)
    bfs_records = BFSTest.objects.filter(user=request.user)
    meridian_records = MeridianTest.objects.filter(user=request.user)
    latest_face = face_records.first()
    latest_bfs = bfs_records.first()
    latest_meridian = meridian_records.first()
    modules = [
        {
            "eyebrow": "QUESTIONNAIRE",
            "label": "健康問卷",
            "description": "更新個人資料、病史與生活習慣，讓後續分析維持最新狀態。",
            "status": "已完成",
            "latest": questionnaire.updated_at,
            "primary_label": "更新問卷",
            "primary_url": reverse("questionnaire") + f"?next={reverse('start_analysis')}",
        },
        {
            "eyebrow": FEATURES["face"]["eyebrow"],
            "label": FEATURES["face"]["label"],
            "description": "上傳正面照，AI 偵測臉部病灶，或查看過去的面診紀錄。",
            "status": f"已有 {face_records.count()} 筆紀錄" if latest_face else "尚無紀錄",
            "latest": latest_face.diagnosis_date if latest_face else None,
            "primary_label": "上傳面診照片",
            "primary_url": reverse("upload_face_diagnosis"),
            "secondary_label": "查看紀錄",
            "secondary_url": reverse("face_list"),
        },
        {
            "eyebrow": FEATURES["bfs"]["eyebrow"],
            "label": FEATURES["bfs"]["label"],
            "description": "上傳報告，或查看同一帳號過去的量測紀錄。",
            "status": f"已有 {bfs_records.count()} 筆紀錄" if latest_bfs else "尚無紀錄",
            "latest": latest_bfs.test_date if latest_bfs else None,
            "primary_label": "上傳 BFS 報告",
            "primary_url": reverse("upload_bfs_test"),
            "secondary_label": "查看紀錄",
            "secondary_url": reverse("bfs_list"),
        },
        {
            "eyebrow": FEATURES["meridian"]["eyebrow"],
            "label": FEATURES["meridian"]["label"],
            "description": "上傳報告，或查看同一帳號過去的檢測紀錄。",
            "status": f"已有 {meridian_records.count()} 筆紀錄" if latest_meridian else "尚無紀錄",
            "latest": latest_meridian.test_date if latest_meridian else None,
            "primary_label": "上傳經絡儀報告",
            "primary_url": reverse("upload_meridian_result"),
            "secondary_label": "查看紀錄",
            "secondary_url": reverse("meridian_list"),
        },
    ]

    return render(
        request,
        "core/analysis_start.html",
        {
            "questionnaire": questionnaire,
            "modules": modules,
            "result_url": reverse("analysis_report", args=[request.user.pk]),
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

    return render(request, "core/feature_page.html", {"feature": feature, "feature_key": feature_key})
