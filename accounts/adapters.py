import logging

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from assessment.services.general_it_trial import provision_signup_trial
from accounts.models import RegistrationRequest, RegistrationSettings

logger = logging.getLogger(__name__)


def apply_registration_approval(user):
    """Apply the site's existing approval policy to one newly saved account."""
    auto_approved = RegistrationSettings.auto_approval_enabled()
    user.is_active = auto_approved
    user.save(update_fields=("is_active",))
    RegistrationRequest.objects.update_or_create(
        user=user,
        defaults={
            "status": (
                RegistrationRequest.Status.APPROVED
                if auto_approved else RegistrationRequest.Status.PENDING
            ),
        },
    )
    return user


class ApprovalAccountAdapter(DefaultAccountAdapter):
    """Keep local signups subject to the configured administrator approval."""

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=commit)
        if commit:
            apply_registration_approval(user)
        return user


class ApprovalSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Apply account approval and trial provisioning to first social signup."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        apply_registration_approval(user)
        try:
            provision_signup_trial(user, request)
        except Exception:
            # Approval/account creation must not be rolled back if trial risk
            # bookkeeping is temporarily unavailable.
            logger.exception("Could not provision General IT trial for social signup")
        return user


# Backwards-compatible import for deployments that briefly used this setting.
TrialSocialAccountAdapter = ApprovalSocialAccountAdapter
