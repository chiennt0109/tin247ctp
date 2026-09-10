from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .admin import UploadTestZipForm, _safe_extract_zip
from .models import Problem, TestCase as ProblemTestCase


@override_settings(PROBLEM_TEST_ZIP_MIN_FREE_SPACE=0)
class TestZipSizeLimitTests(SimpleTestCase):
    @staticmethod
    def archive_with_size(size):
        member = Mock(
            filename="tests/test01.in",
            file_size=size,
            external_attr=0,
        )
        archive = Mock()
        archive.infolist.return_value = [member]
        return archive

    def test_package_larger_than_old_100_mb_limit_is_accepted(self):
        archive = self.archive_with_size(150 * 1024 * 1024)

        _safe_extract_zip(archive, "/tmp")

        archive.extractall.assert_called_once_with("/tmp")

    @override_settings(PROBLEM_TEST_ZIP_MAX_UNCOMPRESSED_SIZE=100 * 1024 * 1024)
    def test_configured_uncompressed_limit_is_enforced(self):
        archive = self.archive_with_size(101 * 1024 * 1024)

        with self.assertRaisesMessage(ValidationError, "tối đa 100 MB"):
            _safe_extract_zip(archive, "/tmp/safe-test-upload")

    @override_settings(PROBLEM_TEST_ZIP_MIN_FREE_SPACE=2 * 1024 * 1024 * 1024)
    @patch("problems.admin.shutil.disk_usage")
    def test_extraction_requires_reserved_disk_space(self, disk_usage):
        disk_usage.return_value = Mock(free=1024 * 1024 * 1024)
        archive = self.archive_with_size(100 * 1024 * 1024)

        with self.assertRaisesMessage(ValidationError, "không đủ dung lượng"):
            _safe_extract_zip(archive, "/tmp/safe-test-upload")

    @override_settings(PROBLEM_TEST_ZIP_MAX_UPLOAD_SIZE=10)
    def test_compressed_upload_limit_is_enforced(self):
        upload = SimpleUploadedFile("tests.zip", b"12345678901")
        form = UploadTestZipForm(files={"zip_file": upload})

        self.assertFalse(form.is_valid())
        self.assertIn("giới hạn", form.errors["zip_file"][0])


class ProblemAdminSampleInlineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="admin-problems",
            email="admin-problems@example.com",
            password="password",
        )
        cls.problem = Problem.objects.create(
            code="INLINE",
            title="Inline test visibility",
            statement="Statement",
        )
        cls.sample = ProblemTestCase.objects.create(
            problem=cls.problem,
            input_data="sample input marker",
            expected_output="sample output marker",
            is_sample=True,
        )
        cls.judge_test = ProblemTestCase.objects.create(
            problem=cls.problem,
            input_data="private judge input marker",
            expected_output="private judge output marker",
            is_sample=False,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_change_form_only_contains_sample_tests(self):
        response = self.client.get(
            reverse("admin:problems_problem_change", args=[self.problem.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sample input marker")
        self.assertContains(response, "sample output marker")
        self.assertNotContains(response, "private judge input marker")
        self.assertNotContains(response, "private judge output marker")

        inline_formset = response.context["inline_admin_formsets"][0].formset
        self.assertEqual(list(inline_formset.queryset), [self.sample])

    def test_inline_forces_new_tests_to_be_samples(self):
        response = self.client.get(
            reverse("admin:problems_problem_change", args=[self.problem.pk])
        )
        formset_class = type(response.context["inline_admin_formsets"][0].formset)
        prefix = response.context["inline_admin_formsets"][0].formset.prefix
        formset = formset_class(
            data={
                f"{prefix}-TOTAL_FORMS": "1",
                f"{prefix}-INITIAL_FORMS": "0",
                f"{prefix}-MIN_NUM_FORMS": "0",
                f"{prefix}-MAX_NUM_FORMS": "1000",
                f"{prefix}-0-is_sample": "",
                f"{prefix}-0-input_data": "new sample",
                f"{prefix}-0-expected_output": "new output",
            },
            instance=self.problem,
            prefix=prefix,
        )

        self.assertTrue(formset.is_valid(), formset.errors)
        new_test = formset.save()[0]
        self.assertTrue(new_test.is_sample)
        self.judge_test.refresh_from_db()
        self.assertFalse(self.judge_test.is_sample)
