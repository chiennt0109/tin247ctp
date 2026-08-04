import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from django.urls import reverse
from django.utils import timezone

from assessment.models import AttemptAnswer, ExamAttempt
from assessment.services.attempt_service import (
    AttemptStateError, StaleAttemptVersion, save_answers, submit_attempt,
)
from assessment.services.start_attempt import start_attempt
from assessment.services.admin_workflow import close_exam_session
from assessment.tests.test_start_attempt import StartAttemptTests


class AttemptServiceTests(TestCase):
    setUp = StartAttemptTests.setUp
    create_question = staticmethod(StartAttemptTests.create_question)
    create_session = StartAttemptTests.create_session
    lock_versions = StartAttemptTests.lock_versions
    open_session = StartAttemptTests.open_session

    def create_attempt(self, username="answerer"):
        user = get_user_model().objects.create_user(username)
        return user, start_attempt(user, self.open_session())

    def test_autosave_uses_optimistic_version_and_rejects_stale_write(self):
        user, attempt = self.create_attempt()
        question = attempt.generated_exam.questions.first()
        saved = save_answers(
            attempt_id=attempt.pk, user=user, expected_version=0,
            answers=[{"question_id": question.pk, "answer": {"value": "1"}}],
        )
        self.assertEqual(saved.data_version, 1)
        self.assertEqual(AttemptAnswer.objects.get().answer, {"value": "1"})

        with self.assertRaises(StaleAttemptVersion):
            save_answers(
                attempt_id=attempt.pk, user=user, expected_version=0,
                answers=[{"question_id": question.pk, "answer": {"value": "2"}}],
            )
        self.assertEqual(AttemptAnswer.objects.get().answer, {"value": "1"})

    def test_answer_from_another_exam_is_rejected(self):
        user, attempt = self.create_attempt("owner")
        other_user = get_user_model().objects.create_user("other")
        other = start_attempt(other_user, attempt.session)
        with self.assertRaisesMessage(AttemptStateError, "không thuộc đề"):
            save_answers(
                attempt_id=attempt.pk, user=user, expected_version=0,
                answers=[{"question_id": other.generated_exam.questions.first().pk, "answer": {"value": "x"}}],
            )
        self.assertFalse(AttemptAnswer.objects.exists())

    def test_submit_is_idempotent_and_prevents_later_edits(self):
        user, attempt = self.create_attempt()
        first = submit_attempt(attempt_id=attempt.pk, user=user)
        second = submit_attempt(attempt_id=attempt.pk, user=user)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(second.status, ExamAttempt.Status.GRADED)
        self.assertIsNotNone(second.submitted_at)
        with self.assertRaises(AttemptStateError):
            save_answers(attempt_id=attempt.pk, user=user, expected_version=0, answers=[])

    def test_closed_session_rejects_autosave(self):
        user, attempt = self.create_attempt("closed-autosave")
        close_exam_session(attempt.session)
        with self.assertRaisesMessage(AttemptStateError, "đã đóng"):
            save_answers(attempt_id=attempt.pk, user=user, expected_version=0, answers=[])

    def test_attempt_row_lock_does_not_join_nullable_generated_exam(self):
        user, attempt = self.create_attempt("postgres-lock")

        with CaptureQueriesContext(connection) as queries:
            submit_attempt(attempt_id=attempt.pk, user=user)

        attempt_selects = [
            item["sql"] for item in queries.captured_queries
            if "SELECT" in item["sql"] and "assessment_examattempt" in item["sql"]
        ]
        self.assertTrue(attempt_selects)
        self.assertTrue(any("JOIN" not in sql for sql in attempt_selects))

    def test_expired_attempt_is_auto_submitted_by_server(self):
        user, attempt = self.create_attempt()
        attempt.expires_at = timezone.now() - timedelta(seconds=1)
        attempt.save(update_fields=("expires_at",))
        result = submit_attempt(attempt_id=attempt.pk, user=user)
        self.assertEqual(result.status, ExamAttempt.Status.GRADED)

    def test_autosave_api_conflict_and_object_permission(self):
        user, attempt = self.create_attempt()
        question = attempt.generated_exam.questions.first()
        self.client.force_login(user)
        url = reverse("assessment:autosave_answers", args=(attempt.pk,))
        payload = {"version": 0, "answers": [{"question_id": question.pk, "answer": {"value": "0"}}]}
        response = self.client.patch(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["version"], 1)
        conflict = self.client.patch(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(conflict.status_code, 409)

        intruder = get_user_model().objects.create_user("intruder")
        self.client.force_login(intruder)
        denied = self.client.patch(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(denied.status_code, 404)

    def test_attempt_page_contains_no_protected_answer_material(self):
        user, attempt = self.create_attempt()
        self.client.force_login(user)
        response = self.client.get(reverse("assessment:attempt_detail", args=(attempt.pk,)))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertNotIn("answer_key", body)
        self.assertNotIn("protected_answer", body)
        self.assertNotIn("question_id_snapshot", body)
        self.assertIn("autoSubmitStarted", body)
        self.assertIn("if(submitting)return", body)

    def test_attempt_page_separates_mcq_true_false_and_has_sticky_navigation(self):
        user, attempt = self.create_attempt("sectioned-attempt")
        questions = list(attempt.generated_exam.questions.select_related("bank_question").order_by("order"))
        true_false = questions[-1]
        true_false.bank_question.question_type = "TRUE_FALSE_GROUP"
        true_false.bank_question.save(update_fields=("question_type",))
        true_false.options_snapshot = []
        true_false.statements_snapshot = [
            {"label": "a", "text": "Nhận định A"},
            {"label": "b", "text": "Nhận định B"},
        ]
        true_false.save(update_fields=("options_snapshot", "statements_snapshot"))
        self.client.force_login(user)

        response = self.client.get(reverse("assessment:attempt_detail", args=(attempt.pk,)))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Phần I — Trắc nghiệm nhiều phương án")
        self.assertContains(response, "Phần II — Trắc nghiệm Đúng/Sai")
        self.assertContains(response, 'class="card question-aside-inner"', html=False)
        self.assertContains(response, "position:sticky;top:145px")
        self.assertContains(response, ".question-aside{align-self:stretch}")
        self.assertContains(response, f'href="#question-{questions[0].pk}"', html=False)
        self.assertContains(response, f'href="#question-{true_false.pk}"', html=False)
        self.assertEqual(
            [row["part_order"] for row in response.context["mcq_rows"]],
            list(range(1, len(questions))),
        )
        self.assertEqual(
            [row["part_order"] for row in response.context["true_false_rows"]],
            [1],
        )
        self.assertContains(response, 'aria-label="Phần II, câu 1"', html=False)

    def test_expired_attempt_page_auto_submits_once_and_redirects(self):
        user, attempt = self.create_attempt("expired-page")
        attempt.expires_at = timezone.now() - timedelta(seconds=1)
        attempt.save(update_fields=("expires_at",))
        self.client.force_login(user)

        response = self.client.get(reverse("assessment:attempt_detail", args=(attempt.pk,)))

        self.assertRedirects(response, reverse("assessment:exam_list"))
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, ExamAttempt.Status.GRADED)
        self.assertIsNotNone(attempt.submitted_at)
