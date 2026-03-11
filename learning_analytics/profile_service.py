from collections import defaultdict

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth

from contests.models import Participation
from submissions.models import Submission

from .ai_coach import AICoach
from .analytics_engine import AnalyticsEngine
from .recommendation_engine import RecommendationEngine
from .skill_engine import SkillEngine
from .models import UserSkill, UserSkillStats


class LearningProfileService:
    CACHE_PREFIX = "user_learning_profile_cache"

    def __init__(self):
        self.skill_engine = SkillEngine()
        self.analytics = AnalyticsEngine()
        self.recommendation = RecommendationEngine()
        self.coach = AICoach()

    @staticmethod
    def mastery_label(score):
        if score < 0.3:
            return "Weak"
        if score < 0.6:
            return "Learning"
        if score < 0.8:
            return "Good"
        return "Mastered"

    def learning_gaps(self, user):
        gaps = []
        mastery = {
            item.skill_id: item.skill_score
            for item in UserSkillStats.objects.filter(user=user).only("skill_id", "skill_score")
        }
        for us in UserSkill.objects.filter(user=user).select_related("skill"):
            if us.skill_score < 0.6:
                continue
            for rel in us.skill.prerequisites.select_related("prerequisite"):
                pre_score = mastery.get(rel.prerequisite_id, 0)
                if pre_score < 0.4:
                    gaps.append(
                        {
                            "skill": us.skill.name,
                            "missing_prerequisite": rel.prerequisite.name,
                            "prerequisite_score": round(pre_score, 4),
                        }
                    )
        return gaps[:10]

    def timeline(self, user):
        monthly = (
            Submission.objects.filter(user=user)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(
                submissions=Count("id"),
                accepted=Count("id", filter=Q(verdict="Accepted")),
            )
            .order_by("month")
        )
        skill_month = (
            UserSkillStats.objects.filter(user=user, skill_score__gte=0.6)
            .annotate(month=TruncMonth("updated_at"))
            .values("month")
            .annotate(skills_learned=Count("id"))
            .order_by("month")
        )

        smap = {x["month"]: x["skills_learned"] for x in skill_month}
        data = []
        for row in monthly:
            m = row["month"]
            data.append(
                {
                    "month": m.strftime("%Y-%m") if m else "unknown",
                    "submissions": row["submissions"],
                    "accepted": row["accepted"],
                    "skills_learned": smap.get(m, 0),
                }
            )
        return data

    def rating_history(self, user):
        parts = Participation.objects.filter(user=user).order_by("contest__end_time").select_related("contest")
        rating = 1200
        history = []
        for p in parts:
            rating += int((p.score * 8) - (p.penalty / 600 if p.penalty else 0))
            history.append(
                {
                    "contest": p.contest.name,
                    "date": p.contest.end_time.strftime("%Y-%m-%d") if p.contest.end_time else "",
                    "rating": max(rating, 0),
                }
            )
        return history

    def build_profile(self, user_id, force=False):
        cache_key = f"{self.CACHE_PREFIX}:{user_id}"
        if not force:
            cached = cache.get(cache_key)
            if cached:
                return cached

        user = User.objects.get(pk=user_id)
        self.skill_engine.update_user_skill_scores(user)

        subs = Submission.objects.filter(user=user)
        accepted = subs.filter(verdict="Accepted")
        total_submissions = subs.count()
        accepted_submissions = accepted.count()
        solved = accepted.values("problem_id").distinct().count()
        acceptance_rate = (accepted_submissions / total_submissions) if total_submissions else 0

        contest_stats = self.analytics.contest_analysis(user)
        weak_skills = self.analytics.compute_weak_skills(user)
        radar = self.analytics.radar_chart(user)
        error_profile = self.analytics.submission_error_profile(user)
        talent = self.analytics.talent_detector(user)
        learning_path = self.recommendation.personalized_learning_path(user)
        recommended_problems = self.recommendation.recommend_problems(user, limit=5)
        training_plan = {
            "daily": self.coach.daily_training_plan(user),
            "weekly": self.coach.weekly_training_plan(user),
        }

        skill_rows = []
        stats_map = {
            s.skill_id: s
            for s in UserSkillStats.objects.filter(user=user).select_related("skill")
        }
        for us in UserSkill.objects.filter(user=user).select_related("skill").order_by("skill__category", "skill__name"):
            st = stats_map.get(us.skill_id)
            attempted = st.attempted_problems if st else 0
            solved_count = st.solved_problems if st else 0
            score = st.skill_score if st else us.skill_score
            skill_rows.append(
                {
                    "skill": us.skill.name,
                    "category": us.skill.category,
                    "level": us.skill.level,
                    "score": round(score, 4),
                    "problems_solved": solved_count,
                    "problems_attempted": attempted,
                    "mastery_status": self.mastery_label(score),
                }
            )

        verdict_counts = defaultdict(int)
        for v in subs.values_list("verdict", flat=True):
            verdict_counts[v] += 1
        total = total_submissions or 1
        behavior = {
            "ac_rate": round(verdict_counts["Accepted"] / total, 4),
            "wa_rate": round(verdict_counts["Wrong Answer"] / total, 4),
            "tle_rate": round(verdict_counts["Time Limit Exceeded"] / total, 4),
            "re_rate": round(verdict_counts["Runtime Error"] / total, 4),
            "patterns": error_profile,
        }

        payload = {
            "user_id": user.id,
            "overview": {
                "username": user.username,
                "join_date": user.date_joined.strftime("%Y-%m-%d"),
                "total_submissions": total_submissions,
                "accepted_submissions": accepted_submissions,
                "acceptance_rate": round(acceptance_rate, 4),
                "problems_solved": solved,
                "contest_participated": contest_stats["contest_count"],
                "current_rating": contest_stats["rating"],
                "talent": talent,
            },
            "skill_radar": radar,
            "skill_progress": skill_rows,
            "weak_skills": [{"skill": w["skill"].name, "weakness": w["weakness_score"]} for w in weak_skills],
            "submission_behavior": behavior,
            "contest_stats": {
                **contest_stats,
                "rating_history": self.rating_history(user),
            },
            "learning_gaps": self.learning_gaps(user),
            "recommended_roadmap": [s.name for s in learning_path[:10]],
            "recommended_problems": [
                {
                    "code": r["problem"].code,
                    "title": r["problem"].title,
                    "difficulty": r["problem"].difficulty,
                    "skill": r["skill"],
                    "score": r["score"],
                }
                for r in recommended_problems
            ],
            "training_plan": training_plan,
            "progress_timeline": self.timeline(user),
        }
        cache.set(cache_key, payload, timeout=6 * 3600)
        return payload
