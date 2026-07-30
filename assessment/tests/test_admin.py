from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assessment.admin import ASSESSMENT_ADMIN_MENU


class AssessmentAdminMenuTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="assessment_admin",
            email="assessment-admin@example.com",
            password="test",
        )
        self.client.force_login(self.admin)

    def test_assessment_menu_is_vietnamese_and_follows_business_workflow(self):
        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        assessment_app = next(
            app for app in response.context["app_list"]
            if app["app_label"] == "assessment"
        )
        self.assertEqual(assessment_app["name"], "Quản lý kiểm tra")

        visible_models = assessment_app["models"]
        expected_models = sorted(
            (
                (order, object_name, label)
                for object_name, (order, label) in ASSESSMENT_ADMIN_MENU.items()
            ),
            key=lambda item: (item[0], item[2]),
        )
        self.assertEqual(
            [(model["object_name"], model["name"]) for model in visible_models],
            [(object_name, label) for _, object_name, label in expected_models],
        )

        labels = [model["name"] for model in visible_models]
        self.assertLess(labels.index("Ngân hàng câu hỏi"), labels.index("Ma trận đề"))
        self.assertLess(labels.index("Ma trận đề"), labels.index("Quy tắc chấm điểm"))
        self.assertLess(labels.index("Quy tắc chấm điểm"), labels.index("Kỳ kiểm tra"))
        self.assertLess(labels.index("Kỳ kiểm tra"), labels.index("Bài làm của học sinh"))
        self.assertLess(
            labels.index("Bài làm của học sinh"),
            labels.index("Nhật ký thao tác kiểm tra"),
        )
