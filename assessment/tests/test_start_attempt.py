from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from assessment.models import ExamAccessGrant, ExamAttempt, ExamSession, GeneratedExam
from assessment.services.exam_generator import ExamGenerationError
from assessment.services.start_attempt import StartAttemptError, start_attempt
from assessment.services.scoring_versioning import lock_scoring_version
from assessment.tests.test_exam_generation import ExamGenerationTests


class StartAttemptTests(TestCase):
    setUp = ExamGenerationTests.setUp
    create_question = staticmethod(ExamGenerationTests.create_question)
    create_session = ExamGenerationTests.create_session
    lock_versions = ExamGenerationTests.lock_versions

    def open_session(self, **kwargs):
        self.lock_versions()
        session = self.create_session(**kwargs)
        now = timezone.now()
        session.opens_at = now - timedelta(minutes=5)
        session.closes_at = now + timedelta(hours=1)
        session.status = ExamSession.Status.OPEN
        session.save(update_fields=("opens_at", "closes_at", "status"))
        return session

    def test_start_and_double_click_create_one_attempt_and_exam(self):
        user = get_user_model().objects.create_user("student")
        session = self.open_session()

        first = start_attempt(user, session)
        second = start_attempt(user, session)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ExamAttempt.objects.count(), 1)
        self.assertEqual(GeneratedExam.objects.count(), 1)
        self.assertEqual(first.generated_exam.questions.count(), 2)

    def test_scheduled_session_transitions_to_open_at_start_time(self):
        user = get_user_model().objects.create_user("scheduled-student")
        session = self.open_session()
        session.status = ExamSession.Status.SCHEDULED
        session.save(update_fields=("status",))
        attempt = start_attempt(user, session)
        session.refresh_from_db()
        self.assertEqual(session.status, ExamSession.Status.OPEN)
        self.assertTrue(attempt.generated_exam_id)

    def test_start_accepts_scoring_version_locked_by_service(self):
        user = get_user_model().objects.create_user("locked-service")
        self.blueprint_version.is_locked = True
        self.blueprint_version.save(update_fields=("is_locked",))
        lock_scoring_version(
            self.scoring_version, blueprint_version=self.blueprint_version,
        )
        session = self.create_session()
        now = timezone.now()
        session.opens_at = now - timedelta(minutes=1)
        session.closes_at = now + timedelta(hours=1)
        session.status = ExamSession.Status.OPEN
        session.save(update_fields=("opens_at", "closes_at", "status"))
        attempt = start_attempt(user, session)
        self.assertTrue(attempt.generated_exam_id)

    def test_users_and_later_attempts_receive_distinct_exams_and_seeds(self):
        first_user = get_user_model().objects.create_user("first")
        second_user = get_user_model().objects.create_user("second")
        session = self.open_session()
        session.max_attempts = 2
        session.save(update_fields=("max_attempts",))
        first = start_attempt(first_user, session)
        other = start_attempt(second_user, session)
        first.status = ExamAttempt.Status.SUBMITTED
        first.save(update_fields=("status",))
        retry = start_attempt(first_user, session)

        self.assertEqual(retry.attempt_number, 2)
        self.assertEqual(len({first.generated_exam_id, other.generated_exam_id, retry.generated_exam_id}), 3)
        self.assertNotEqual(first.generated_exam.seed, retry.generated_exam.seed)

    def test_max_attempts_time_and_access_are_enforced(self):
        user = get_user_model().objects.create_user("limited")
        session = self.open_session()
        attempt = start_attempt(user, session)
        attempt.status = ExamAttempt.Status.SUBMITTED
        attempt.save(update_fields=("status",))
        with self.assertRaisesMessage(StartAttemptError, "hết số lượt"):
            start_attempt(user, session)

        session.max_attempts = 2
        session.closes_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=("max_attempts", "closes_at"))
        with self.assertRaisesMessage(StartAttemptError, "Ngoài thời gian"):
            start_attempt(user, session)

        session.closes_at = timezone.now() + timedelta(hours=1)
        session.access_mode = ExamSession.AccessMode.SELECTED_GROUPS
        session.save(update_fields=("closes_at", "access_mode"))
        with self.assertRaisesMessage(StartAttemptError, "không có quyền"):
            start_attempt(user, session)

    def test_user_grants_have_independent_attempt_limits(self):
        one_attempt = get_user_model().objects.create_user("one-attempt")
        three_attempts = get_user_model().objects.create_user("three-attempts")
        session = self.open_session()
        session.access_mode = ExamSession.AccessMode.ACCESS_GRANTS
        session.save(update_fields=("access_mode",))
        ExamAccessGrant.objects.create(
            session=session, user=one_attempt,
            limit_mode=ExamAccessGrant.LimitMode.ATTEMPTS, max_attempts=1,
        )
        ExamAccessGrant.objects.create(
            session=session, user=three_attempts,
            limit_mode=ExamAccessGrant.LimitMode.ATTEMPTS, max_attempts=3,
        )

        first = start_attempt(one_attempt, session)
        first.status = ExamAttempt.Status.SUBMITTED
        first.save(update_fields=("status",))
        with self.assertRaisesMessage(StartAttemptError, "hết số lượt"):
            start_attempt(one_attempt, session)

        for number in range(3):
            attempt = start_attempt(three_attempts, session)
            self.assertEqual(attempt.attempt_number, number + 1)
            attempt.status = ExamAttempt.Status.SUBMITTED
            attempt.save(update_fields=("status",))

    def test_group_time_grant_controls_access_and_attempt_deadline(self):
        user = get_user_model().objects.create_user("timed-group-user")
        group = Group.objects.create(name="Timed candidates")
        user.groups.add(group)
        session = self.open_session()
        session.access_mode = ExamSession.AccessMode.ACCESS_GRANTS
        session.save(update_fields=("access_mode",))
        valid_until = timezone.now() + timedelta(minutes=10)
        grant = ExamAccessGrant.objects.create(
            session=session, group=group,
            limit_mode=ExamAccessGrant.LimitMode.VALIDITY,
            valid_from=timezone.now() - timedelta(minutes=1), valid_until=valid_until,
        )

        attempt = start_attempt(user, session)
        self.assertLessEqual(attempt.expires_at, valid_until)

        attempt.status = ExamAttempt.Status.SUBMITTED
        attempt.save(update_fields=("status",))
        grant.valid_until = timezone.now() - timedelta(seconds=1)
        grant.save(update_fields=("valid_until",))
        attempts_before = ExamAttempt.objects.count()
        exams_before = GeneratedExam.objects.count()
        with self.assertRaisesMessage(StartAttemptError, "hết hạn"):
            start_attempt(user, session)
        self.assertEqual(ExamAttempt.objects.count(), attempts_before)
        self.assertEqual(GeneratedExam.objects.count(), exams_before)

    def test_direct_user_grant_overrides_group_grant(self):
        user = get_user_model().objects.create_user("direct-over-group")
        group = Group.objects.create(name="Broad candidates")
        user.groups.add(group)
        session = self.open_session()
        session.access_mode = ExamSession.AccessMode.ACCESS_GRANTS
        session.save(update_fields=("access_mode",))
        ExamAccessGrant.objects.create(
            session=session, group=group,
            limit_mode=ExamAccessGrant.LimitMode.ATTEMPTS, max_attempts=3,
        )
        ExamAccessGrant.objects.create(
            session=session, user=user,
            limit_mode=ExamAccessGrant.LimitMode.ATTEMPTS, max_attempts=1,
        )
        attempt = start_attempt(user, session)
        attempt.status = ExamAttempt.Status.SUBMITTED
        attempt.save(update_fields=("status",))

        with self.assertRaisesMessage(StartAttemptError, "hết số lượt"):
            start_attempt(user, session)

    def test_insufficient_pool_and_generator_error_roll_back_everything(self):
        user = get_user_model().objects.create_user("rollback")
        session = self.open_session()
        self.slot.quantity = 20
        self.slot.save(update_fields=("quantity",))
        with self.assertRaises(StartAttemptError):
            start_attempt(user, session)
        self.assertFalse(ExamAttempt.objects.exists())
        self.assertFalse(GeneratedExam.objects.exists())

        self.slot.quantity = 2
        self.slot.save(update_fields=("quantity",))
        with patch("assessment.services.start_attempt.ExamGenerator.generate_for_attempt", side_effect=ExamGenerationError("boom")):
            with self.assertRaisesMessage(StartAttemptError, "boom"):
                start_attempt(user, session)
        self.assertFalse(ExamAttempt.objects.exists())
        self.assertFalse(GeneratedExam.objects.exists())

    def test_student_attempt_page_never_exposes_protected_answers(self):
        user = get_user_model().objects.create_user("debug")
        attempt = start_attempt(user, self.open_session())
        self.client.force_login(user)

        response = self.client.get(reverse("assessment:attempt_detail", args=(attempt.pk,)))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "answer_key")
        self.assertNotContains(response, "correct_answer")
        self.assertNotContains(response, "protected_answer")
