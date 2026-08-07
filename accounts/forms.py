# accounts/forms.py
import logging

from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import SetPasswordForm
from allauth.account.forms import SignupForm
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from assessment.services.general_it_trial import provision_signup_trial

logger = logging.getLogger(__name__)


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
    # Honeypot: bot sẽ điền, người thật không thấy
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Leave empty"
    )

    # reCAPTCHA thực sự
    captcha = ReCaptchaField(
        widget=ReCaptchaV2Checkbox,
        label="Xác thực bạn không phải robot"
    )

    def clean_honeypot(self):
        value = self.cleaned_data.get("honeypot", "")
        if value.strip() != "":
            # nếu honeypot bị điền => nghi là bot
            raise forms.ValidationError("Bot detected.")
        return value

    def save(self, request):
        # gọi save gốc của allauth để tạo user
        user = super().save(request)
        # Trial failures must not roll back or break the user's DMOJ account.
        try:
            provision_signup_trial(user, request)
        except Exception:
            logger.exception("Could not provision General IT trial")
        return user
