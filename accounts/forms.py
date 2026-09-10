import secrets

from allauth.account.forms import SignupForm
from django import forms
from django.core import signing
from django.utils.crypto import salted_hmac
from django.contrib.auth.password_validation import validate_password


CAPTCHA_SALT = "accounts.signup-captcha"
CAPTCHA_MAX_AGE = 10 * 60


def captcha_numbers(nonce):
    """Derive operands server-side; the answer is never present in the token."""
    digest = salted_hmac(CAPTCHA_SALT, nonce).digest()
    return digest[0] % 8 + 2, digest[1] % 8 + 2


class SecureSignupForm(SignupForm):
    """Signup form with a self-hosted, expiring and single-use challenge."""

    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Leave empty",
    )
    captcha_token = forms.CharField(widget=forms.HiddenInput)
    captcha_answer = forms.IntegerField(
        label="Kết quả phép tính",
        min_value=0,
        max_value=100,
        error_messages={
            "required": "Vui lòng nhập kết quả phép tính.",
            "invalid": "Kết quả phải là một số.",
        },
        widget=forms.NumberInput(
            attrs={
                "inputmode": "numeric",
                "autocomplete": "off",
                "placeholder": "Nhập kết quả",
                "aria-describedby": "captcha-question",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            token = self.data.get("captcha_token", "")
            self.fields["captcha_token"].initial = token
            self.captcha_question = self._question_from_token(token)
        else:
            nonce = secrets.token_urlsafe(16)
            left, right = captcha_numbers(nonce)
            token = signing.dumps(
                {"nonce": nonce},
                salt=CAPTCHA_SALT,
                compress=True,
            )
            self.fields["captcha_token"].initial = token
            self.captcha_question = f"{left} + {right} = ?"

    @staticmethod
    def _question_from_token(token):
        try:
            payload = signing.loads(token, salt=CAPTCHA_SALT, max_age=CAPTCHA_MAX_AGE)
            left, right = captcha_numbers(payload["nonce"])
            return f"{left} + {right} = ?"
        except (signing.BadSignature, KeyError, TypeError):
            return "Thử thách đã hết hạn"

    def clean_honeypot(self):
        value = self.cleaned_data.get("honeypot", "")
        if value.strip():
            raise forms.ValidationError("Không thể xử lý yêu cầu này.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        token = cleaned_data.get("captcha_token")
        answer = cleaned_data.get("captcha_answer")
        if not token or answer is None:
            return cleaned_data

        try:
            payload = signing.loads(token, salt=CAPTCHA_SALT, max_age=CAPTCHA_MAX_AGE)
            nonce = payload["nonce"]
            left, right = captcha_numbers(nonce)
            expected = left + right
        except (signing.BadSignature, signing.SignatureExpired, KeyError, TypeError, ValueError):
            self.add_error("captcha_answer", "Thử thách đã hết hạn. Vui lòng tải lại trang.")
            return cleaned_data

        if not secrets.compare_digest(str(answer), str(expected)):
            self.add_error("captcha_answer", "Kết quả chưa đúng. Vui lòng thử lại.")
            return cleaned_data

        return cleaned_data

    def save(self, request):
        return super().save(request)


class PasswordResetRequestForm(forms.Form):
    identifier = forms.CharField(
        max_length=254,
        label="Tên đăng nhập hoặc email",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )
    captcha_token = forms.CharField(widget=forms.HiddenInput)
    captcha_answer = forms.IntegerField(
        label="Kết quả phép tính",
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.is_bound:
            token = self.data.get("captcha_token", "")
            self.fields["captcha_token"].initial = token
            self.captcha_question = SecureSignupForm._question_from_token(token)
        else:
            nonce = secrets.token_urlsafe(16)
            left, right = captcha_numbers(nonce)
            token = signing.dumps({"nonce": nonce}, salt=CAPTCHA_SALT, compress=True)
            self.fields["captcha_token"].initial = token
            self.captcha_question = f"{left} + {right} = ?"

    def clean(self):
        data = super().clean()
        token = data.get("captcha_token")
        answer = data.get("captcha_answer")
        if not token or answer is None:
            return data
        try:
            payload = signing.loads(token, salt=CAPTCHA_SALT, max_age=CAPTCHA_MAX_AGE)
            left, right = captcha_numbers(payload["nonce"])
        except (signing.BadSignature, KeyError, TypeError):
            self.add_error("captcha_answer", "Thử thách đã hết hạn. Vui lòng tải lại trang.")
            return data
        if not secrets.compare_digest(str(answer), str(left + right)):
            self.add_error("captcha_answer", "Kết quả chưa đúng. Vui lòng thử lại.")
        return data


class PasswordResetConfirmForm(forms.Form):
    identifier = forms.CharField(max_length=254, label="Tên đăng nhập hoặc email")
    reset_code = forms.CharField(
        max_length=32,
        label="Mã đặt lại mật khẩu",
        widget=forms.TextInput(attrs={"autocomplete": "one-time-code", "placeholder": "XXXX-XXXX-XXXX"}),
    )
    new_password1 = forms.CharField(
        label="Mật khẩu mới",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Nhập lại mật khẩu mới",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean(self):
        data = super().clean()
        password = data.get("new_password1")
        if password and password != data.get("new_password2"):
            self.add_error("new_password2", "Hai mật khẩu không trùng khớp.")
        if password:
            try:
                validate_password(password)
            except forms.ValidationError as error:
                self.add_error("new_password1", error)
        return data
