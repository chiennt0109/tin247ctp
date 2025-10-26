# accounts/forms.py
from django import forms
from allauth.account.forms import SignupForm
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox  # dùng loại checkbox v2

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
        # bạn có thể gán thêm role mặc định, nhóm lớp,... tại đây
        return user
