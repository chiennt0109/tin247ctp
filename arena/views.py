from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.db.models import Max
from django.contrib.auth.decorators import login_required, user_passes_test

from .models import ArenaGame, ArenaRun, ArenaProgress
from .forms import SnakeRunForm
from .sandbox import run_bot_in_sandbox, SandboxError

from arena.games.robot_step import (
    random_secret,
    build_input as build_input_egg,
    parse_move,
    simulate_robot_stateful,
    result_to_json as robot_json
)

from arena.games.Bai1.robot_step_chick import build_input_chick, judge_chick
from arena.games.Bai1.robot_step_teen import build_input_teen, judge_teen


def _admin_only(u):
    return u.is_staff or u.is_superuser

def arena_access_required(view):
    return login_required(user_passes_test(_admin_only)(view))


# ======================
# 🔥 BỊ MẤT — THÊM LẠI
# ======================
@arena_access_required
def game_list(request):
    games = ArenaGame.objects.filter(is_active=True)
    return render(request, "arena/game_list.html", {"games": games})
# ======================


@arena_access_required
def robot_play(request):
    game = get_object_or_404(ArenaGame, slug="robot-step")
    user = request.user

    progress, _ = ArenaProgress.objects.get_or_create(user=user, game=game)

    mode = request.GET.get("mode", "egg")
    if mode not in ["egg", "chick", "teen"]:
        mode = "egg"

    run_instance = None
    replay = None

    if request.method == "POST":
        form = SnakeRunForm(request.POST)

        if form.is_valid():
            arena_run = form.save(commit=False)
            arena_run.game = game
            arena_run.user = user

            # Build input theo mode
            if mode == "egg":
                secret = random_secret()
                bot_input = build_input_egg(secret)
                meta = {"secret": secret}

            elif mode == "chick":
                bot_input, meta = build_input_chick()

            else:
                bot_input, meta = build_input_teen()

            try:
                stdout = run_bot_in_sandbox(
                    language=arena_run.language,
                    source_code=arena_run.source_code,
                    stdin_data=bot_input,
                    time_limit=0.5,
                )

                move = parse_move(stdout)

                if mode == "egg":
                    # STATEFUL SIMULATION
                    result = simulate_robot_stateful(
                        secret=secret,
                        move=move,
                        x=progress.current_x,
                        y=progress.current_y,
                    )

                    # Update vị trí
                    progress.current_x = result.new_x
                    progress.current_y = result.new_y
                    progress.save()

                    replay = {
                        "before": result.before,
                        "after": result.after,
                        "secret": secret,
                        "bot_move": move,
                        "score": result.score,
                        "status": result.status,
                        "error": result.error
                    }

                    arena_run.score = result.score
                    arena_run.status = result.status
                    arena_run.replay_json = robot_json(result)

                elif mode == "chick":
                    score, status = judge_chick(stdout, meta)
                    arena_run.score = score
                    arena_run.status = status
                    replay = {"score": score, "status": status, "meta": meta}

                else:
                    score, status = judge_teen(stdout, meta)
                    arena_run.score = score
                    arena_run.status = status
                    replay = {"score": score, "status": status, "meta": meta}

                arena_run.steps = 1
                arena_run.save()

                run_instance = arena_run

                if mode == "egg":
                    progress.update_after_run("egg", arena_run.score, 10)
                elif mode == "chick":
                    progress.update_after_run("chick", arena_run.score, 12)
                else:
                    progress.update_after_run("teen", arena_run.score, 12)

            except SandboxError as e:
                messages.error(request, f"Sandbox Error: {e}")

    else:
        form = SnakeRunForm()

    # Ranking
    agg = (
        ArenaRun.objects.filter(game=game, user__isnull=False)
        .values("user__username")
        .annotate(best_score=Max("score"))
        .order_by("-best_score")
    )

    return render(request, "arena/robot_play.html", {
        "game": game,
        "form": form,
        "run": run_instance,
        "replay": replay,
        "mode": mode,
        "progress": progress,
        "top_ranks": agg[:10],
    })
