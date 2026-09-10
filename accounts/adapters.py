from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import RegistrationRequest, RegistrationSettings


def apply_registration_approval(user):
    """Apply the approval policy to a newly-created local or social account."""
    approved = RegistrationSettings.auto_approval_enabled()
    user.is_active = approved
    user.save(update_fields=("is_active",))
    RegistrationRequest.objects.update_or_create(
        user=user,
        defaults={
            "status": (
                RegistrationRequest.Status.APPROVED
                if approved
                else RegistrationRequest.Status.PENDING
            )
        },
    )
    return user


class ApprovalAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=commit)
        if commit:
            apply_registration_approval(user)
        return user


class ApprovalSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        return apply_registration_approval(user)
