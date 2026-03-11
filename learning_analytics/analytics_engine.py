from django.db.models import Avg, Count, F, Q

from contests.models import Participation
from submissions.models import Submission

from .models import Skill, UserSkill, UserSkillStats, UserTopicStats


class AnalyticsEngine:
    def compute_weak_skills(self, user, limit=5):
        topics = UserTopicStats.objects.filter(user=user).select_related("skill")
        stats_map = {
            item.skill_id: item
            for item in UserSkillStats.objects.filter(user=user).only("skill_id", "skill_score")
        }
        ranked = []
        for topic in topics:
            unsolved_ratio = 1 - (topic.solved / topic.attempted) if topic.attempted else 1
            low_skill_score = 1 - stats_map.get(topic.skill_id).skill_score if topic.skill_id in stats_map else 1
            weakness_score = (
                0.4 * (1 - topic.acceptance_rate)
                + 0.3 * unsolved_ratio
                + 0.3 * low_skill_score
            )
            UserSkill.objects.filter(user=user, skill=topic.skill).update(weakness_score=weakness_score)
            ranked.append({"skill": topic.skill, "weakness_score": round(weakness_score, 4)})
        ranked.sort(key=lambda x: x["weakness_score"], reverse=True)
        return ranked[:limit]

    def contest_analysis(self, user):
        parts = Participation.objects.filter(user=user)
        contest_count = parts.count()
        avg_rank = 0
        if contest_count:
            avg_rank = parts.aggregate(avg_rank=Avg("penalty")).get("avg_rank") or 0

        contest_subs = Submission.objects.filter(user=user, contest__isnull=False)
        contest_attempted = contest_subs.values("problem_id").distinct().count()
        contest_solved = contest_subs.filter(verdict="Accepted").values("problem_id").distinct().count()
        problem_solve_rate = contest_solved / contest_attempted if contest_attempted else 0

        practice_subs = Submission.objects.filter(user=user, contest__isnull=True)
        practice_attempted = practice_subs.values("problem_id").distinct().count()
        practice_solved = practice_subs.filter(verdict="Accepted").values("problem_id").distinct().count()
        practice_rate = practice_solved / practice_attempted if practice_attempted else 0

        flags = []
        avg_exec = contest_subs.aggregate(v=Avg("exec_time")).get("v") or 0
        wa_rate = (
            contest_subs.filter(verdict="Wrong Answer").count() / contest_subs.count()
            if contest_subs.exists()
            else 0
        )
        if avg_exec > 1.5:
            flags.append("slow solving")
        if wa_rate > 0.45:
            flags.append("high WA")
        if practice_rate > problem_solve_rate + 0.2:
            flags.append("contest anxiety")

        return {
            "contest_count": contest_count,
            "avg_rank": round(avg_rank, 2),
            "rating": round((practice_rate * 1500) + (contest_count * 10), 2),
            "problem_solve_rate": round(problem_solve_rate, 4),
            "flags": flags,
        }

    def submission_error_profile(self, user):
        subs = Submission.objects.filter(user=user)
        total = subs.count() or 1
        wa = subs.filter(verdict="Wrong Answer").count() / total
        tle = subs.filter(verdict="Time Limit Exceeded").count() / total
        re = subs.filter(verdict="Runtime Error").count() / total

        def label(rate):
            if rate >= 0.4:
                return "high"
            if rate >= 0.2:
                return "medium"
            return "low"

        return {
            "logic_errors": label(wa),
            "complexity_understanding": label(tle),
            "implementation_bugs": label(re),
        }

    def radar_chart(self, user):
        roots = ["Graph", "Dynamic Programming", "Math", "String", "Data Structures", "Greedy"]
        data = {}
        for root in roots:
            root_skills = Skill.objects.filter(Q(name=root) | Q(parent__name=root))
            avg = (
                UserSkill.objects.filter(user=user, skill__in=root_skills).aggregate(v=Avg("skill_score")).get("v")
                or 0
            )
            data[root.lower().replace(" ", "_")] = round(avg, 4)
        return data

    def talent_detector(self, user):
        subs = Submission.objects.filter(user=user)
        hard_solved = (
            subs.filter(problem__difficulty="Hard", verdict="Accepted").values("problem_id").distinct().count()
        )
        solve_speed = 1 - min((subs.aggregate(v=Avg("exec_time")).get("v") or 2) / 4, 1)
        contest = self.contest_analysis(user)
        rating_growth = min(contest["rating"] / 2000, 1)
        contest_rank = 1 - min(contest["avg_rank"] / 100, 1)

        talent_score = (
            0.3 * min(hard_solved / 50, 1)
            + 0.3 * rating_growth
            + 0.2 * solve_speed
            + 0.2 * contest_rank
        )
        if talent_score > 0.75:
            level = "olympiad_candidate"
        elif talent_score > 0.5:
            level = "promising"
        else:
            level = "normal"
        return {"talent_score": round(talent_score, 4), "level": level}
