from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

PHONE_ERROR = "請輸入正確的手機號碼，例如：0912345678。"


def normalize_phone_number(value):
    digits = "".join(char for char in str(value or "") if char.isdigit())
    if digits.startswith("886") and len(digits) == 12:
        digits = f"0{digits[3:]}"
    return digits


def is_valid_phone_number(value):
    return len(value) == 10 and value.startswith("09") and value.isdigit()


class RegisterForm(UserCreationForm):
    username = forms.CharField(
        label="手機號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例如：0912345678",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )
    email = forms.EmailField(
        label="電子信箱",
        required=False,
        widget=forms.EmailInput(
            attrs={
                "class": "form-control",
                "placeholder": "example@email.com",
                "autocomplete": "email",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
        labels = {
            "username": "手機號碼",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "密碼"
        self.fields["password2"].label = "確認密碼"
        self.fields["password1"].widget.attrs.update(
            {"class": "form-control", "placeholder": "請輸入密碼", "autocomplete": "new-password"}
        )
        self.fields["password2"].widget.attrs.update(
            {"class": "form-control", "placeholder": "請再次輸入密碼", "autocomplete": "new-password"}
        )

    def clean_username(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("username"))
        if not is_valid_phone_number(phone_number):
            raise forms.ValidationError(PHONE_ERROR)
        if User.objects.filter(username=phone_number).exists():
            raise forms.ValidationError("這支手機號碼已經註冊過，請直接登入。")
        return phone_number


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "手機號碼或密碼不正確，請再確認一次。",
        "inactive": "此帳號目前無法使用。",
    }
    username = forms.CharField(
        label="手機號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "例如：0912345678",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )
    password = forms.CharField(
        label="密碼",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "請輸入密碼", "autocomplete": "current-password"}
        ),
    )
    remember_me = forms.BooleanField(
        label="讓我保持登入",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "remember-checkbox"}),
    )

    def clean_username(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("username"))
        if not is_valid_phone_number(phone_number):
            raise forms.ValidationError(PHONE_ERROR)
        return phone_number


class PhonePasswordResetForm(forms.Form):
    phone_number = forms.CharField(
        label="手機號碼",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "請輸入註冊時使用的手機號碼",
                "inputmode": "tel",
                "autocomplete": "tel",
            }
        ),
    )
    new_password1 = forms.CharField(
        label="新密碼",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "請輸入新密碼", "autocomplete": "new-password"}
        ),
    )
    new_password2 = forms.CharField(
        label="確認新密碼",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "placeholder": "請再次輸入新密碼", "autocomplete": "new-password"}
        ),
    )

    def clean_phone_number(self):
        phone_number = normalize_phone_number(self.cleaned_data.get("phone_number"))
        if not is_valid_phone_number(phone_number):
            raise forms.ValidationError(PHONE_ERROR)

        self.user = User.objects.filter(username=phone_number).first()
        if self.user is None:
            raise forms.ValidationError("查無此手機號碼，請先建立帳號。")
        return phone_number

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")

        if password1 and password2 and password1 != password2:
            self.add_error("new_password2", "兩次輸入的密碼不一致。")

        if password1 and hasattr(self, "user"):
            validate_password(password1, self.user)

        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user