# -*- coding: utf-8 -*-


import time
import logging
from typing import List
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.urls import resolve

logger = logging.getLogger("submission_throttle")

class SubmissionThrottleMiddleware:
    RATE_LIMIT = getattr(settings, "SUBMISSION_THROTTLE_RATE", 5)
    TIME_WINDOW = getattr(settings, "SUBMISSION_THROTTLE_WINDOW", 60)
    ENABLED = getattr(settings, "SUBMISSION_THROTTLE_ENABLED", True)

    TARGET_VIEW_NAMES: List[str] = getattr(
        settings,
        "SUBMISSION_THROTTLE_VIEWS",
        ["submissions:submission_create"],
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self.ENABLED or request.method != "POST":
            return self.get_response(request)

        try:
            match = resolve(request.path_info)
            view_name = getattr(match, "view_name", "") or ""
        except Exception as e:
            logger.warning("[THROTTLE] cannot resolve path=%s err=%s", request.path_info, e)
            return self.get_response(request)

        # Only throttle judge submissions, not roadmap/API
        if view_name not in self.TARGET_VIEW_NAMES:
            return self.get_response(request)

        username = getattr(request.user, "username", "anonymous")

        # bypass staff
        if getattr(request, "user", None) and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                logger.info("[THROTTLE] staff bypass user=%s", username)
                return self.get_response(request)

        try:
            blocked = self._check_rate_limit(request, username)
            if blocked:
                return blocked
        except Exception as e:
            logger.error("[THROTTLE] rate-limit error: %s", e, exc_info=True)
            return self.get_response(request)

        logger.info("[THROTTLE] allowed user=%s path=%s", username, request.path_info)
        return self.get_response(request)

    # ================= helpers =================
    def _cache_key_for(self, request) -> str:
        if getattr(request, "user", None) and request.user.is_authenticated:
            return f"throttle:submit:user:{request.user.id}"
        ip = self._client_ip(request)
        return f"throttle:submit:ip:{ip}"

    def _check_rate_limit(self, request, username: str):
        now = time.time()
        key = self._cache_key_for(request)
        history = []

        try:
            history = cache.get(key, [])
        except Exception as e:
            logger.error("[THROTTLE] cache.get failed user=%s err=%s", username, e)

        # Keep only recent timestamps
        history = [t for t in history if now - t < self.TIME_WINDOW]

        if len(history) >= self.RATE_LIMIT:
            logger.warning("[THROTTLE] blocked user=%s path=%s", username, request.path_info)
            return self._too_many(history)

        history.append(now)
        try:
            cache.set(key, history, timeout=self.TIME_WINDOW)
        except Exception as e:
            logger.error("[THROTTLE] cache.set failed user=%s err=%s", username, e)
        return None

    def _too_many(self, history):
        retry_after = max(1, int(self.TIME_WINDOW - (time.time() - history[0])))
        payload = {
            "ok": False,
            "error": "You are submitting too fast. Please wait a moment.",
            "retry_after": retry_after,
            "limit": self.RATE_LIMIT,
            "window": self.TIME_WINDOW,
        }
        resp = JsonResponse(payload, status=429)
        resp["Retry-After"] = str(retry_after)
        return resp

    @staticmethod
    def _client_ip(request) -> str:
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "") or "unknown"
