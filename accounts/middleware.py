from django.conf import settings

from assessment.services.general_it_trial import COOKIE_NAME, new_device_id, request_device_id


class TrialDeviceCookieMiddleware:
    """Issue an opaque device signal; it is never an authentication credential."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.trial_device_id = request_device_id(request)
        response = self.get_response(request)
        if request.COOKIES.get(COOKIE_NAME) != request.trial_device_id:
            response.set_cookie(
                COOKIE_NAME, request.trial_device_id,
                max_age=int(getattr(settings, "TRIAL_DEVICE_COOKIE_MAX_AGE_DAYS", 365)) * 86400,
                secure=request.is_secure(), httponly=True, samesite="Lax",
            )
        return response
