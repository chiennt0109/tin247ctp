from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from assessment.admin import ScoringRuleInline, ScoringSchemeVersionAdmin
from assessment.models import ScoringRule, ScoringScheme, ScoringSchemeVersion
from assessment.services.scoring_versioning import clone_scoring_version, lock_scoring_version


class ScoringVersioningTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("scoring-admin", password="x")
        self.scheme = ScoringScheme.objects.create(name="Quy tắc")
        self.version = ScoringSchemeVersion.objects.create(
            scheme=self.scheme, version=1, total_score=10, rounding_digits=2,
        )
        self.rule = ScoringRule.objects.create(
            version=self.version, question_type="MCQ_SINGLE", rule_code="MCQ",
            max_score=1, configuration={"mode": "exact"}, order=1,
        )
        self.request = RequestFactory().get("/admin/")
        self.request.user = self.user

    def test_draft_rule_can_be_changed(self):
        self.rule.max_score = 2
        self.rule.full_clean()
        self.rule.save()
        self.assertEqual(ScoringRule.objects.get(pk=self.rule.pk).max_score, 2)

    def test_lock_only_updates_parent_and_does_not_save_rules(self):
        with patch.object(ScoringRule, "save", autospec=True) as rule_save:
            locked = lock_scoring_version(self.version, actor=self.user)
        self.assertTrue(locked.is_locked)
        rule_save.assert_not_called()

    def test_locked_admin_is_readonly_and_cannot_add_change_or_delete_rules(self):
        lock_scoring_version(self.version, actor=self.user)
        inline = ScoringRuleInline(ScoringSchemeVersion, admin.site)
        version_admin = ScoringSchemeVersionAdmin(ScoringSchemeVersion, admin.site)
        self.assertFalse(inline.has_add_permission(self.request, self.version))
        self.assertFalse(inline.has_change_permission(self.request, self.version))
        self.assertFalse(inline.has_delete_permission(self.request, self.version))
        self.assertIn("configuration", inline.get_readonly_fields(self.request, self.version))
        self.assertEqual(
            set(version_admin.get_readonly_fields(self.request, self.version)),
            {field.name for field in ScoringSchemeVersion._meta.fields},
        )

    def test_clone_locked_version_creates_editable_draft_with_rules(self):
        lock_scoring_version(self.version, actor=self.user)
        clone = clone_scoring_version(self.version, actor=self.user)
        self.assertEqual(clone.version, 2)
        self.assertFalse(clone.is_locked)
        self.assertEqual(clone.rules.count(), 1)
        cloned_rule = clone.rules.get()
        cloned_rule.max_score = 3
        cloned_rule.full_clean()
        cloned_rule.save()
