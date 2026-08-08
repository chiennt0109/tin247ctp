from django.contrib import admin
from django.db.models import Count, Q

from .models import Submission


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    """Submission list with filters and a per-user summary for administrators."""

    change_list_template = "admin/submissions/submission/change_list.html"
    list_display = (
        "id",
        "user",
        "problem",
        "verdict",
        "language",
        "created_at",
    )
    list_filter = ("created_at", "user", "verdict")
    search_fields = ("user__username", "user__email", "problem__code", "problem__title")
    list_select_related = ("user", "problem")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        # The parent may return a redirect for an invalid/normalized query string.
        if not hasattr(response, "context_data") or not response.context_data:
            return response

        changelist = response.context_data["cl"]
        filtered_submissions = changelist.queryset
        totals = filtered_submissions.aggregate(
            submission_count=Count("id"),
            accepted_count=Count("id", filter=Q(verdict="Accepted")),
            user_count=Count("user_id", distinct=True),
        )
        user_summary = (
            filtered_submissions.values(
                "user_id",
                "user__username",
                "user__first_name",
                "user__last_name",
                "user__email",
            )
            .annotate(
                submission_count=Count("id"),
                accepted_count=Count("id", filter=Q(verdict="Accepted")),
            )
            .order_by("-submission_count", "user__username")
        )

        response.context_data.update(
            submission_totals=totals,
            submission_user_summary=user_summary,
        )
        return response
