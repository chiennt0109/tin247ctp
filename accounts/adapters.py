import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from assessment.services.general_it_trial import provision_signup_trial

logger = logging.getLogger(__name__)


class TrialSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Provision the same trial for first-time social signups, never for login."""

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        try:
            provision_signup_trial(user, request)
        except Exception:
            logger.exception("Could not provision General IT trial for social signup")
        return user
