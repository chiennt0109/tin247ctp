from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.core import signing

from .forms import CAPTCHA_SALT, SecureSignupForm, captcha_numbers

from .adapters import apply_registration_approval
from .models import RegistrationRequest, RegistrationSettings


class SignupCaptchaTests(SimpleTestCase):
    def test_signup_form_creates_signed_math_challenge(self):
        form = SecureSignupForm()
        token = form.fields["captcha_token"].initial
        payload = signing.loads(token, salt=CAPTCHA_SALT)

        self.assertEqual(set(payload), {"nonce"})
        left, right = captcha_numbers(payload["nonce"])
        self.assertEqual(form.captcha_question, f"{left} + {right} = ?")

    def test_tampered_challenge_is_rejected(self):
        form = SecureSignupForm(
            data={"captcha_token": "tampered", "captcha_answer": 4}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("hết hạn", form.errors["captcha_answer"][0])


class RegistrationApprovalTests(TestCase):
    def test_new_registration_is_inactive_by_default(self):
        user = get_user_model().objects.create_user("pending", password="A-secure-pass-123")

        apply_registration_approval(user)

        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertEqual(user.registration_request.status, RegistrationRequest.Status.PENDING)

    def test_auto_approval_activates_new_registration(self):
        RegistrationSettings.objects.create(auto_approve=True)
        user = get_user_model().objects.create_user("automatic", password="A-secure-pass-123")

        apply_registration_approval(user)

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(user.registration_request.status, RegistrationRequest.Status.APPROVED)

    def test_approval_and_rejection_keep_auth_state_in_sync(self):
        reviewer = get_user_model().objects.create_superuser("admin", "admin@example.com", "A-secure-pass-123")
        user = get_user_model().objects.create_user("student", password="A-secure-pass-123")
        apply_registration_approval(user)

        user.registration_request.approve(reviewer)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

        user.registration_request.reject(reviewer)
        user.refresh_from_db()
        self.assertFalse(user.is_active)
