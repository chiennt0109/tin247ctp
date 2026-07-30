from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AssessmentNavigationTests(TestCase):
    def test_exam_list_requires_existing_login(self):
        response = self.client.get(reverse("assessment:exam_list"))

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_authenticated_user_sees_empty_assessment_page(self):
        user = get_user_model().objects.create_user("assessment_student", password="test")
        self.client.force_login(user)

        response = self.client.get(reverse("assessment:exam_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tin học đại trà")
        self.assertContains(response, "Chưa có kỳ kiểm tra")
        content = response.content.decode()
        self.assertLess(content.index("🐱 Scratch"), content.index("📝 Tin học đại trà"))
