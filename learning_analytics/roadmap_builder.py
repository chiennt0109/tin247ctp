from django.utils.text import slugify

from learning_analytics.models import LearningTrack, LearningTrackStep, Skill

TRACKS = {
    "graph": ("Graph Track", "Graph Algorithms"),
    "dynamic-programming": ("Dynamic Programming Track", "Dynamic Programming"),
    "math": ("Math Track", "Mathematics"),
    "data-structures": ("Data Structures Track", "Data Structures"),
    "string-algorithms": ("String Algorithms Track", "Strings"),
}


class RoadmapBuilder:
    def _ordered_skills(self, category):
        skills = list(Skill.objects.filter(category=category).prefetch_related("prerequisites__prerequisite", "problem_skills__problem"))
        skills_map = {s.id: s for s in skills}
        visited, temp, ordered = set(), set(), []

        def dfs(skill):
            if skill.id in visited:
                return
            if skill.id in temp:
                return
            temp.add(skill.id)
            for rel in skill.prerequisites.all():
                if rel.prerequisite_id in skills_map:
                    dfs(skills_map[rel.prerequisite_id])
            temp.remove(skill.id)
            visited.add(skill.id)
            ordered.append(skill)

        for sk in skills:
            dfs(sk)
        return ordered

    def build_all(self):
        built = {}
        for slug, (track_name, category) in TRACKS.items():
            track, _ = LearningTrack.objects.update_or_create(
                slug=slug,
                defaults={"track_name": track_name, "category": category},
            )
            track.steps.all().delete()

            order = 1
            for skill in self._ordered_skills(category):
                problem = (
                    skill.problem_skills.select_related("problem")
                    .order_by("problem__difficulty_rating", "problem__ac_count")
                    .first()
                )
                problem_obj = problem.problem if problem else None
                difficulty = problem_obj.difficulty_level if problem_obj else ""
                LearningTrackStep.objects.create(
                    track=track,
                    order=order,
                    skill=skill,
                    problem=problem_obj,
                    difficulty=difficulty,
                )
                order += 1
            built[slug] = track_name
        return built

    def get_track(self, slug):
        track = LearningTrack.objects.filter(slug=slug).prefetch_related("steps__skill", "steps__problem").first()
        if not track:
            return None
        return {
            "track": track.track_name,
            "slug": track.slug,
            "steps": [
                {
                    "order": step.order,
                    "skill": step.skill.name,
                    "problem": step.problem.code if step.problem else None,
                    "difficulty": step.difficulty,
                }
                for step in track.steps.all()
            ],
        }
