from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from assessment.models import ExamAttempt, ExamSession, GradingResult
from assessment.services.attempt_service import save_answers, submit_attempt
from assessment.services.grading import grade_attempt
from assessment.services.result_release import result_visibility
from assessment.services.start_attempt import start_attempt
from assessment.tests.test_start_attempt import StartAttemptTests


class GradingTests(TestCase):
    setUp = StartAttemptTests.setUp
    create_question = staticmethod(StartAttemptTests.create_question)
    create_session = StartAttemptTests.create_session
    lock_versions = StartAttemptTests.lock_versions
    open_session = StartAttemptTests.open_session

    def test_submit_grades_snapshot_and_is_idempotent(self):
        user = get_user_model().objects.create_user("graded-student")
        attempt = start_attempt(user, self.open_session())
        first_question = attempt.generated_exam.questions.order_by("order").first()
        displayed_correct_index = first_question.option_order.index(0)
        save_answers(
            attempt_id=attempt.pk, user=user, expected_version=0,
            answers=[{
                "question_id": first_question.pk,
                "answer": {"value": str(displayed_correct_index)},
            }],
        )

        submitted = submit_attempt(attempt_id=attempt.pk, user=user)
        again = submit_attempt(attempt_id=attempt.pk, user=user)

        self.assertEqual(submitted.status, ExamAttempt.Status.GRADED)
        self.assertEqual(again.status, ExamAttempt.Status.GRADED)
        self.assertEqual(GradingResult.objects.count(), 1)
        result = GradingResult.objects.get()
        self.assertEqual(result.total_score, Decimal("0.25"))
        self.assertEqual(result.correct_count, 1)
        self.assertEqual(result.blank_count, 1)
        self.assertNotIn("answer_key", str(result.detail))

    def test_regrade_preserves_history_and_switches_current_result(self):
        user = get_user_model().objects.create_user("regraded-student")
        attempt = start_attempt(user, self.open_session())
        submit_attempt(attempt_id=attempt.pk, user=user)
        first = GradingResult.objects.get(is_current=True)

        second = grade_attempt(attempt.pk, actor=user, reason="Kiểm tra lại", allow_regrade=True)

        first.refresh_from_db()
        self.assertFalse(first.is_current)
        self.assertTrue(second.is_current)
        self.assertEqual(second.sequence, 2)
        self.assertEqual(GradingResult.objects.count(), 2)

    def test_result_release_hides_score_and_question_outcomes_until_allowed(self):
        user = get_user_model().objects.create_user("release-student")
        session = self.open_session()
        session.score_release_mode = ExamSession.ReleaseMode.MANUAL
        session.answer_release_mode = ExamSession.ReleaseMode.NEVER
        session.save(update_fields=("score_release_mode", "answer_release_mode"))
        attempt = start_attempt(user, session)
        submit_attempt(attempt_id=attempt.pk, user=user)
        attempt.refresh_from_db()
        self.client.force_login(user)

        hidden = self.client.get(reverse("assessment:attempt_result", args=(attempt.pk,)))
        self.assertContains(hidden, "đang chờ công bố")
        self.assertNotContains(hidden, str(attempt.score))

        session.score_release_mode = ExamSession.ReleaseMode.AFTER_SUBMIT
        session.save(update_fields=("score_release_mode",))
        visible = self.client.get(reverse("assessment:attempt_result", args=(attempt.pk,)))
        self.assertContains(visible, "Điểm")
        self.assertContains(visible, str(attempt.score))
        self.assertContains(visible, "chưa được công bố")
        self.assertFalse(result_visibility(attempt)["answers"])
