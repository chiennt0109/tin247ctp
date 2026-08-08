from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase

from accounts.adapters import (
    ApprovalAccountAdapter, ApprovalSocialAccountAdapter, apply_registration_approval,
)
from accounts.forms import (
    CAPTCHA_SALT, PasswordResetConfirmForm, PasswordResetRequestForm,
    SecureSignupForm, captcha_numbers,
)
from accounts.models import RegistrationRequest, RegistrationSettings


class PasswordResetFormCompatibilityTests(TestCase):
    def test_request_form_normalizes_email(self):
        form = PasswordResetRequestForm({"email": " Student@Example.COM "})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["email"], "student@example.com")

    def test_confirm_form_validates_and_saves_password(self):
        user = get_user_model().objects.create_user("reset-user", password="old-password-123")
        form = PasswordResetConfirmForm(user, {
            "new_password1": "new-password-456!",
            "new_password2": "new-password-456!",
        })
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        user.refresh_from_db()
        self.assertTrue(user.check_password("new-password-456!"))


class ApprovalAdapterTests(TestCase):
    def test_configured_adapter_classes_are_importable(self):
        self.assertTrue(issubclass(ApprovalAccountAdapter, object))
        self.assertTrue(issubclass(ApprovalSocialAccountAdapter, object))

    def test_new_user_is_pending_when_auto_approval_is_disabled(self):
        RegistrationSettings.objects.create(auto_approve=False)
        user = get_user_model().objects.create_user("pending-user")

        apply_registration_approval(user)

        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.registration_request.status, RegistrationRequest.Status.PENDING)

    def test_new_user_is_active_when_auto_approval_is_enabled(self):
        RegistrationSettings.objects.create(auto_approve=True)
        user = get_user_model().objects.create_user("approved-user", is_active=False)

        apply_registration_approval(user)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.registration_request.status, RegistrationRequest.Status.APPROVED)


class SecureSignupFormTests(TestCase):
    def test_unbound_form_builds_a_signed_math_challenge(self):
        form = SecureSignupForm()

        token = form.fields["captcha_token"].initial
        payload = signing.loads(token, salt=CAPTCHA_SALT)
        left, right = captcha_numbers(payload["nonce"])

        self.assertEqual(form.captcha_question, f"{left} + {right} = ?")

    def test_bound_form_rejects_an_incorrect_challenge_answer(self):
        initial = SecureSignupForm()
        token = initial.fields["captcha_token"].initial
        payload = signing.loads(token, salt=CAPTCHA_SALT)
        left, right = captcha_numbers(payload["nonce"])
        form = SecureSignupForm(data={
            "username": "captcha-user",
            "email": "captcha@example.com",
            "password1": "safe-password-123!",
            "password2": "safe-password-123!",
            "captcha_token": token,
            "captcha_answer": left + right + 1,
            "honeypot": "",
        })

        self.assertFalse(form.is_valid())
        self.assertIn("captcha_answer", form.errors)
