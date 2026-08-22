from django.contrib.auth import authenticate, get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.core import signing
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from .forms import CAPTCHA_SALT, SecureSignupForm, captcha_numbers

from .adapters import apply_registration_approval
from .models import PasswordResetRequest, RegistrationRequest, RegistrationSettings


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


class GoogleLoginTemplateTests(TestCase):
    def test_login_starts_google_oauth_with_post(self):
        response = self.client.get(reverse("account_login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'method="post"')
        self.assertContains(response, reverse("google_login"))
        self.assertNotContains(response, f'<a href="{reverse("google_login")}"')

    def test_google_confirmation_posts_to_current_provider_url(self):
        response = self.client.get(reverse("google_login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<form method="post"')
        self.assertContains(response, "Tiếp tục với Google")


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


@override_settings(CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}})
class PasswordResetSecurityTests(TestCase):
    old_password = "Old-password-123!"
    new_password = "New-password-456!"

    def setUp(self):
        self.user_a = get_user_model().objects.create_user(
            "user-a", "a@example.com", self.old_password
        )
        self.user_b = get_user_model().objects.create_user(
            "user-b", "b@example.com", self.old_password
        )
        self.admin = get_user_model().objects.create_superuser(
            "reset-admin", "admin@example.com", "Admin-password-123!"
        )

    def _request_reset(self, identifier):
        form = SecureSignupForm()
        token = form.fields["captcha_token"].initial
        payload = signing.loads(token, salt=CAPTCHA_SALT)
        left, right = captcha_numbers(payload["nonce"])
        return self.client.post(reverse("account_reset_password"), {
            "identifier": identifier,
            "captcha_token": token,
            "captcha_answer": left + right,
        })

    def _issue(self, user=None):
        reset_request = PasswordResetRequest.objects.create(user=user or self.user_a)
        return reset_request, reset_request.issue(self.admin)

    def _confirm(self, identifier, code, password=None):
        password = password or self.new_password
        return self.client.post(reverse("account_reset_password_confirm_code"), {
            "identifier": identifier,
            "reset_code": code,
            "new_password1": password,
            "new_password2": password,
        })

    def test_request_does_not_change_password_or_account_state(self):
        old_hash = self.user_a.password
        response = self._request_reset("user-a")
        self.user_a.refresh_from_db()
        self.assertRedirects(response, reverse("account_reset_password"))
        self.assertEqual(self.user_a.password, old_hash)
        self.assertTrue(self.user_a.is_active)
        self.assertIsNotNone(authenticate(username="user-a", password=self.old_password))

    def test_unknown_request_has_same_response_and_does_not_lock_user(self):
        real = self._request_reset("user-a")
        fake = self._request_reset("does-not-exist@example.com")
        self.user_a.refresh_from_db()
        self.assertEqual(real.status_code, fake.status_code)
        self.assertEqual(real.url, fake.url)
        self.assertTrue(self.user_a.is_active)
        self.assertTrue(self.user_a.check_password(self.old_password))

    def test_repeated_requests_do_not_create_duplicate_pending_rows(self):
        self._request_reset("user-a")
        self._request_reset("a@example.com")
        self.assertEqual(
            PasswordResetRequest.objects.filter(
                user=self.user_a, status=PasswordResetRequest.Status.PENDING
            ).count(),
            1,
        )

    def test_issued_code_is_not_a_password_and_old_password_still_works(self):
        _, code = self._issue()
        self.assertIsNone(authenticate(username="user-a", password=code))
        self.assertIsNotNone(authenticate(username="user-a", password=self.old_password))

    def test_plaintext_code_is_not_stored(self):
        reset_request, code = self._issue()
        reset_request.refresh_from_db()
        self.assertNotEqual(reset_request.token_hash, PasswordResetRequest.normalize_code(code))
        self.assertNotIn(PasswordResetRequest.normalize_code(code), reset_request.token_hash)
        self.assertGreater(reset_request.expires_at, timezone.now() + timedelta(hours=23, minutes=59))

    def test_wrong_code_does_not_change_password(self):
        self._issue()
        self._confirm("user-a", "AAAA-BBBB-CCCC")
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password(self.old_password))

    def test_code_is_bound_to_its_user(self):
        _, code = self._issue(self.user_a)
        self._issue(self.user_b)
        self._confirm("user-b", code)
        self.user_b.refresh_from_db()
        self.assertTrue(self.user_b.check_password(self.old_password))

    def test_expired_code_is_rejected_without_password_change(self):
        reset_request, code = self._issue()
        reset_request.expires_at = timezone.now() - timedelta(seconds=1)
        reset_request.save(update_fields=("expires_at",))
        self._confirm("user-a", code)
        reset_request.refresh_from_db()
        self.user_a.refresh_from_db()
        self.assertEqual(reset_request.status, PasswordResetRequest.Status.EXPIRED)
        self.assertTrue(self.user_a.check_password(self.old_password))

    def test_used_code_cannot_be_reused_and_password_changes_only_on_success(self):
        reset_request, code = self._issue()
        self.assertTrue(self.user_a.check_password(self.old_password))
        response = self._confirm("user-a", code)
        self.assertRedirects(response, reverse("account_login"))
        self.user_a.refresh_from_db()
        reset_request.refresh_from_db()
        self.assertFalse(self.user_a.check_password(self.old_password))
        self.assertTrue(self.user_a.check_password(self.new_password))
        self.assertEqual(reset_request.status, PasswordResetRequest.Status.COMPLETED)
        self.assertIsNotNone(reset_request.used_at)
        self._confirm("user-a", code, "Another-password-789!")
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password(self.new_password))

    def test_new_code_immediately_invalidates_old_code(self):
        old_request, old_code = self._issue()
        new_request, new_code = self._issue()
        old_request.refresh_from_db()
        self.assertEqual(old_request.status, PasswordResetRequest.Status.EXPIRED)
        self._confirm("user-a", old_code)
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password(self.old_password))
        self._confirm("user-a", new_code)
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password(self.new_password))
