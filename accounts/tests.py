from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.adapters import (
    ApprovalAccountAdapter, ApprovalSocialAccountAdapter, apply_registration_approval,
)
from accounts.forms import PasswordResetConfirmForm, PasswordResetRequestForm
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
