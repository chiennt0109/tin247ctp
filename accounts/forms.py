# accounts/forms.py
import logging
import secrets

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import SetPasswordForm
from django.core import signing
from django.utils.crypto import salted_hmac
from allauth.account.forms import SignupForm
from assessment.services.general_it_trial import provision_signup_trial

logger = logging.getLogger(__name__)
CAPTCHA_SALT = "accounts.signup-captcha"
CAPTCHA_MAX_AGE = 10 * 60


def captcha_numbers(nonce):
    """Derive operands server-side so the signed token contains no answer."""
    digest = salted_hmac(CAPTCHA_SALT, nonce).digest()
    return digest[0] % 8 + 2, digest[1] % 8 + 2


class PasswordResetRequestForm(forms.Form):
    """Request data used by the project's password-reset views.

    Deliberately performs only input validation here; the view owns token
    creation and must return the same response for existing and unknown email
    addresses to avoid account enumeration.
    """

    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()


class PasswordResetConfirmForm(SetPasswordForm):
    """Compatibility form for the existing custom password-reset views."""

    new_password1 = forms.CharField(
        label="Mật khẩu mới",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="Nhập lại mật khẩu mới",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )


class SecureSignupForm(SignupForm):
    """Signup form with a self-hosted, signed and expiring challenge."""

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
        # gọi save gốc của allauth để tạo user
        user = super().save(request)
        # Trial failures must not roll back or break the user's DMOJ account.
        try:
            provision_signup_trial(user, request)
        except Exception:
            logger.exception("Could not provision General IT trial")
        return user
