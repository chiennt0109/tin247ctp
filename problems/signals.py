# path: problems/signals.py
# -*- coding: utf-8 -*-
import os
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from problems.models import TestCase, Problem

SANDBOX_ROOT = "/srv/judge/testcases"

def _write_testcase_files(problem):
    in_dir = os.path.join(SANDBOX_ROOT, problem.code, "in")
    out_dir = os.path.join(SANDBOX_ROOT, problem.code, "out")
    os.makedirs(in_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    for d in (in_dir, out_dir):
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))

    tcs = TestCase.objects.filter(problem=problem).order_by("id")
    for i, tc in enumerate(tcs, start=1):
        with open(os.path.join(in_dir, f"{i:02d}.inp"), "w", encoding="utf-8") as fi:
            fi.write((tc.input_data or "").strip() + "\n")
        with open(os.path.join(out_dir, f"{i:02d}.out"), "w", encoding="utf-8") as fo:
            fo.write((tc.expected_output or "").strip() + "\n")
    print(f"[AUTO-SYNC] {problem.code}: {tcs.count()} testcases written.")


@receiver(post_save, sender=TestCase)
def sync_on_save(sender, instance, **kwargs):
    _write_testcase_files(instance.problem)


@receiver(post_delete, sender=TestCase)
def sync_on_delete(sender, instance, **kwargs):
    _write_testcase_files(instance.problem)


@receiver(post_delete, sender=Problem)
def delete_sandbox_folder(sender, instance, **kwargs):
    p_dir = os.path.join(SANDBOX_ROOT, instance.code)
    if os.path.exists(p_dir):
        import shutil
        shutil.rmtree(p_dir)
        print(f"[AUTO-CLEAN] Removed sandbox folder for {instance.code}")
