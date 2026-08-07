
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from assessment.models import TrialAccountLink, TrialAuditEvent, TrialDevice, TrialEntitlement
from assessment.services.general_it_trial import (
    COOKIE_NAME, provision_signup_trial, request_device_id,
)
from accounts.middleware import TrialDeviceCookieMiddleware


class GeneralITTrialProvisioningTests(TestCase):
    def request(self, device=None, ip="203.0.113.10"):
        request = RequestFactory().get("/accounts/signup/", REMOTE_ADDR=ip)
        request.COOKIES = {}
        if device:
            request.COOKIES[COOKIE_NAME] = device
        request.trial_device_id = request_device_id(request)
        return request

    def test_new_account_gets_active_trial_eligibility(self):
        user = get_user_model().objects.create_user("trial-one")
        entitlement = provision_signup_trial(user, self.request())
        self.assertEqual(entitlement.status, TrialEntitlement.Status.ACTIVE)
        self.assertEqual(user.general_it_trial_link.entitlement, entitlement)

    def test_accounts_on_same_device_share_one_entitlement(self):
        device = "d54e9ec9-c3bc-45cb-8305-1d57cd2c41cc"
        first = get_user_model().objects.create_user("shared-one")
        second = get_user_model().objects.create_user("shared-two")
        first_entitlement = provision_signup_trial(first, self.request(device))
        second_entitlement = provision_signup_trial(second, self.request(device))
        self.assertEqual(first_entitlement, second_entitlement)
        self.assertEqual(TrialEntitlement.objects.count(), 1)
        self.assertEqual(TrialAccountLink.objects.count(), 2)

    def test_same_public_ip_does_not_merge_different_devices(self):
        first = get_user_model().objects.create_user("school-one")
        second = get_user_model().objects.create_user("school-two")
        one = provision_signup_trial(
            first, self.request("59dcaa95-946b-431b-86f5-8abc37db652b", "198.51.100.5"),
        )
        two = provision_signup_trial(
            second, self.request("ce2c9a83-c51b-472b-a94d-184356558a33", "198.51.100.5"),
        )
        self.assertNotEqual(one, two)
        self.assertEqual(one.status, TrialEntitlement.Status.ACTIVE)
        self.assertEqual(two.status, TrialEntitlement.Status.ACTIVE)

    @override_settings(TRIAL_SIGNUP_IP_LIMIT_HOUR=1, TRIAL_SIGNUP_IP_LIMIT_DAY=20)
    def test_ip_burst_flags_trial_but_does_not_block_account(self):
        first = get_user_model().objects.create_user("burst-one")
        second = get_user_model().objects.create_user("burst-two")
        provision_signup_trial(
            first, self.request("91b783d0-64b7-4933-918a-c631f15ef9de", "192.0.2.7"),
        )
        flagged = provision_signup_trial(
            second, self.request("c39e74e9-fc56-4e6a-bfa5-c87c50341498", "192.0.2.7"),
        )
        self.assertTrue(get_user_model().objects.filter(pk=second.pk).exists())
        self.assertEqual(flagged.status, TrialEntitlement.Status.REVIEW_REQUIRED)
        self.assertTrue(TrialAuditEvent.objects.filter(event_type="SIGNUP_REVIEW_REQUIRED").exists())

    def test_missing_or_invalid_cookie_is_replaced_without_crashing(self):
        request = self.request()
        request.COOKIES[COOKIE_NAME] = "not-a-uuid"
        self.assertEqual(len(request_device_id(request)), 36)

    def test_only_hashes_are_persisted(self):
        raw = "5a05adee-cb98-4e87-803e-a35344c0a4a1"
        user = get_user_model().objects.create_user("hashed-device")
        provision_signup_trial(user, self.request(raw))
        device = TrialDevice.objects.get()
        self.assertNotEqual(device.device_hash, raw)
        self.assertEqual(len(device.device_hash), 64)

    def test_middleware_sets_opaque_long_lived_secure_cookie_on_https(self):
        request = RequestFactory().get("/accounts/signup/", secure=True)
        response = TrialDeviceCookieMiddleware(lambda _request: HttpResponse("ok"))(request)
        cookie = response.cookies[COOKIE_NAME]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(int(cookie["max-age"]), 365 * 86400)

    def test_deleting_account_preserves_device_and_entitlement(self):
        user = get_user_model().objects.create_user("discarded-account")
        entitlement = provision_signup_trial(
            user, self.request("2dd166b7-1761-4f89-a79a-d73d7501df43"),
        )
        user.delete()
        self.assertTrue(TrialEntitlement.objects.filter(pk=entitlement.pk).exists())
        self.assertTrue(TrialDevice.objects.filter(entitlement=entitlement).exists())
        self.assertTrue(TrialAccountLink.objects.filter(entitlement=entitlement, user=None).exists())
