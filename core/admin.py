from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.admin.sites import NotRegistered
from django import forms

from .models import(
    Questionnaire,
    BFSTest,
    BFSTestFile,
    MeridianTest,
    MeridianReading,
    FaceDiagnosis,
)
from .forms.auth import (
    PHONE_ERROR,
    is_valid_phone_number,
    normalize_phone_number,
    validate_name_part,
)
from .services.subjects import get_subject_display_name


try:
    admin.site.unregister(User)
except NotRegistered:
    pass


class PhoneAccountFormMixin:
    phone_help_text = "這是登入用手機號碼，不是姓名；姓名請填在姓氏與名字欄位。"

    def configure_account_fields(self):
        if "username" in self.fields:
            self.fields["username"].label = "手機號碼（登入帳號）"
            self.fields["username"].help_text = self.phone_help_text
            self.fields["username"].widget.attrs.update(
                {"inputmode": "tel", "autocomplete": "tel"}
            )
        if "last_name" in self.fields:
            self.fields["last_name"].label = "姓氏"
            self.fields["last_name"].help_text = "例如：王。"
        if "first_name" in self.fields:
            self.fields["first_name"].label = "名字"
            self.fields["first_name"].help_text = "例如：小明。"

    def clean_username(self):
        raw_username = self.cleaned_data.get("username", "")
        phone_number = normalize_phone_number(raw_username)
        original_username = getattr(self.instance, "username", "")

        if original_username and raw_username == original_username:
            return raw_username

        if not is_valid_phone_number(phone_number):
            raise forms.ValidationError(PHONE_ERROR)

        users = User.objects.filter(username=phone_number)
        if getattr(self.instance, "pk", None):
            users = users.exclude(pk=self.instance.pk)
        if users.exists():
            raise forms.ValidationError("這支手機號碼已經被其他帳號使用。")

        return phone_number


class PhoneUserChangeForm(PhoneAccountFormMixin, UserChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure_account_fields()

    def clean_last_name(self):
        last_name = self.cleaned_data.get("last_name", "")
        return validate_name_part(last_name) if last_name else ""

    def clean_first_name(self):
        first_name = self.cleaned_data.get("first_name", "")
        return validate_name_part(first_name) if first_name else ""

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if (
            email
            and User.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError("這個電子信箱已被其他帳號使用。")
        return email


class PhoneUserCreationForm(PhoneAccountFormMixin, UserCreationForm):
    last_name = forms.CharField(label="姓氏", max_length=40)
    first_name = forms.CharField(label="名字", max_length=80)
    email = forms.EmailField(label="電子郵件", required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("last_name", "first_name", "username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configure_account_fields()

    def clean_last_name(self):
        return validate_name_part(self.cleaned_data.get("last_name"))

    def clean_first_name(self):
        return validate_name_part(self.cleaned_data.get("first_name"))

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("這個電子信箱已被其他帳號使用。")
        return email


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = PhoneUserChangeForm
    add_form = PhoneUserCreationForm
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("個人資料", {"fields": ("last_name", "first_name", "email")}),
        (
            "權限",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("重要日期", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "last_name",
                    "first_name",
                    "username",
                    "email",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    list_display = (
        "display_name",
        "login_phone",
        "email",
        "is_staff",
        "is_active",
    )
    list_display_links = ("display_name", "login_phone")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("last_name", "first_name", "username")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("questionnaire")

    @admin.display(description="姓名")
    def display_name(self, obj):
        return get_subject_display_name(obj)

    @admin.display(description="手機號碼（登入帳號）", ordering="username")
    def login_phone(self, obj):
        return obj.username


class SubjectRecordAdminMixin:
    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        if "user" in form.base_fields:
            form.base_fields["user"].required = True
            form.base_fields["user"].label = "受測者帳號"
            form.base_fields[
                "user"
            ].help_text = "每筆資料都要綁定到一個受測者帳號，避免日後查詢與歷史紀錄混在一起。"
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "user":
            kwargs["queryset"] = User.objects.filter(is_active=True).order_by(
                "last_name",
                "first_name",
                "username",
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Questionnaire)
class QuestionnaireAdmin(SubjectRecordAdminMixin, admin.ModelAdmin):
    list_display = ("name", "user", "gender", "blood_type", "updated_at")
    list_filter = ("gender", "blood_type", "exercise", "surgery_history", "updated_at")
    search_fields = ("name", "user__username", "user__email", "notes")
    date_hierarchy = "updated_at"
    ordering = ("-updated_at",)
    list_select_related = ("user",)
    list_per_page = 25


@admin.register(BFSTest)
class BFSTestAdmin(SubjectRecordAdminMixin, admin.ModelAdmin):
    list_display = ("patient_name", "user", "test_date", "needs_date_review", "updated_at")
    list_filter = ("needs_date_review", "test_date", "updated_at")
    search_fields = ("patient_name", "user__username", "user__email", "notes")
    date_hierarchy = "test_date"
    ordering = ("-test_date",)
    list_select_related = ("user",)
    list_per_page = 25


@admin.register(BFSTestFile)
class BFSTestFileAdmin(admin.ModelAdmin):
    list_display = ("bfs_test", "file_number", "analysis_status", "uploaded_at")
    list_filter = ("analysis_status", "uploaded_at")
    search_fields = (
        "bfs_test__patient_name",
        "bfs_test__user__username",
        "bfs_test__user__email",
        "file_description",
        "detected_template",
    )
    date_hierarchy = "uploaded_at"
    list_select_related = ("bfs_test", "bfs_test__user")
    list_per_page = 25


@admin.register(MeridianTest)
class MeridianTestAdmin(SubjectRecordAdminMixin, admin.ModelAdmin):
    list_display = ("patient_name", "user", "test_date", "gender", "age", "updated_at")
    list_filter = ("gender", "test_date", "updated_at")
    search_fields = (
        "patient_name",
        "user__username",
        "user__email",
        "birth_date",
        "notes",
    )
    date_hierarchy = "test_date"
    ordering = ("-test_date",)
    list_select_related = ("user",)
    list_per_page = 25


@admin.register(MeridianReading)
class MeridianReadingAdmin(admin.ModelAdmin):
    list_display = ("meridian_test", "meridian", "left_org", "right_org")
    search_fields = ("meridian_test__patient_name", "meridian")
    list_filter = ("meridian",)
    list_select_related = ("meridian_test",)
    list_per_page = 25


@admin.register(FaceDiagnosis)
class FaceDiagnosisAdmin(SubjectRecordAdminMixin, admin.ModelAdmin):
    list_display = ("patient_name", "user", "diagnosis_date", "updated_at")
    list_filter = ("diagnosis_date", "updated_at")
    search_fields = ("patient_name", "user__username", "user__email", "notes")
    date_hierarchy = "diagnosis_date"
    ordering = ("-diagnosis_date",)
    list_select_related = ("user",)
    list_per_page = 25
