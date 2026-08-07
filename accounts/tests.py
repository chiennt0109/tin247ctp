from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.forms import PasswordResetConfirmForm, PasswordResetRequestForm


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
