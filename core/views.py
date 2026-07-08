from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import LoginForm, PhonePasswordResetForm, QuestionnaireForm, RegisterForm
from .models import Questionnaire


FEATURES = {
    "face": {
        "label": "面診影像觀察",
        "eyebrow": "FACE IMAGE",
        "action": "立即測試",
        "description": "上傳或拍攝臉部影像，作為後續視覺化觀察與健康狀態參考。",
    },
    "bfs": {
        "label": "BFS量測結果",
        "eyebrow": "BFS DATA",
        "action": "查看分析",
        "description": "整理 BFS 量測資料，建立個人生理狀態的參考分析頁面。",
    },
    "meridian": {
        "label": "經絡檢測分析",
        "eyebrow": "MERIDIAN",
        "action": "查看分析",
        "description": "整合經絡檢測資訊，呈現更完整的健康評估概念。",
    },
}


def home(request):
    return render(request, "core/index.html")


def safe_next_url(request, fallback):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return next_url
    return fallback


def questionnaire_start_url():
    return f"{reverse('questionnaire')}?next={reverse('start_analysis')}"


def register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "註冊成功，歡迎開始使用健康分析平台。")
            return redirect(safe_next_url(request, questionnaire_start_url()))
    else:
        form = RegisterForm()

    return render(
        request,
        "core/auth_form.html",
        {
            "form": form,
            "mode": "register",
            "title": "建立帳號",
            "subtitle": "使用手機號碼建立帳號，後續即可填寫健康問卷並使用各項分析功能。",
            "submit_label": "註冊",
            "switch_text": "已經有帳號？",
            "switch_url": reverse("login"),
            "switch_label": "前往登入",
            "next_url": request.GET.get("next", ""),
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 14)
            else:
                request.session.set_expiry(0)
            messages.success(request, "登入成功。")
            return redirect(safe_next_url(request, reverse("start_analysis")))
    else:
        form = LoginForm(request)

    return render(
        request,
        "core/auth_form.html",
        {
            "form": form,
            "mode": "login",
            "title": "會員登入",
            "subtitle": "登入後可填寫健康問卷、進行健康分析與查看個人結果。",
            "submit_label": "登入",
            "switch_text": "還沒有帳號？",
            "switch_url": reverse("register"),
            "switch_label": "建立帳號",
            "next_url": request.GET.get("next", ""),
        },
    )


def forgot_password_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = PhonePasswordResetForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "密碼已更新，請使用手機號碼重新登入。")
            return redirect("login")
    else:
        form = PhonePasswordResetForm()

    return render(
        request,
        "core/auth_form.html",
        {
            "form": form,
            "mode": "forgot",
            "title": "忘記密碼",
            "subtitle": "請輸入註冊手機號碼並設定新密碼。此頁目前作為畢專展示流程，尚未串接簡訊驗證。",
            "method_note": "手機號碼重設密碼",
            "submit_label": "更新密碼",
            "switch_text": "想起密碼了？",
            "switch_url": reverse("login"),
            "switch_label": "返回登入",
            "next_url": request.GET.get("next", ""),
        },
    )


def logout_view(request):
    logout(request)
    messages.info(request, "已登出。")
    return redirect("home")


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
            "url": reverse("feature_gate", args=["bfs"]),
        },
        {
            "eyebrow": FEATURES["meridian"]["eyebrow"],
            "label": FEATURES["meridian"]["label"],
            "description": FEATURES["meridian"]["description"],
            "action": FEATURES["meridian"]["action"],
            "url": reverse("feature_gate", args=["meridian"]),
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

    return render(request, "core/feature_page.html", {"feature": feature, "feature_key": feature_key})
