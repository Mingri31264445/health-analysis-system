from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from ..forms import LoginForm, PhonePasswordResetForm, RegisterForm
from ..models import Questionnaire
from .permissions import can_view_all_records


def safe_next_url(request, fallback):
    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return next_url
    return fallback


def questionnaire_start_url():
    return f"{reverse('questionnaire')}?next={reverse('start_analysis')}"


def default_auth_redirect(user):
    if can_view_all_records(user):
        return reverse("dashboard")

    if Questionnaire.objects.filter(user=user).exists():
        return reverse("start_analysis")

    return questionnaire_start_url()


def register_view(request):
    if request.user.is_authenticated:
        return redirect(default_auth_redirect(request.user))

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "註冊成功，歡迎開始使用健康分析平台。")
            return redirect(safe_next_url(request, default_auth_redirect(user)))
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
        return redirect(default_auth_redirect(request.user))

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            if form.cleaned_data.get("remember_me"):
                request.session.set_expiry(60 * 60 * 24 * 14)
            else:
                request.session.set_expiry(0)
            messages.success(request, "登入成功。")
            return redirect(safe_next_url(request, default_auth_redirect(form.get_user())))
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
