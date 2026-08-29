from django.test import SimpleTestCase, override_settings


@override_settings(DEBUG=False)
class ErrorPageSecurityTests(SimpleTestCase):
    def test_not_found_page_does_not_disclose_url_configuration(self):
        response = self.client.get("/this-route-must-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Không tìm thấy trang", status_code=404)
        self.assertNotContains(response, "Using the URLconf", status_code=404)
        self.assertNotContains(response, "Raised by", status_code=404)
