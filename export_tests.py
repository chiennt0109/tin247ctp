# -*- coding: utf-8 -*-
"""
Standalone exporter: run with
    python export_tests.py
to dump all Problem testcases -> /srv/judge/testcases
"""
import os, sys

# --- Force correct Django environment ---
PROJECT_DIR = "/var/www/tin247ctp"
sys.path.insert(0, PROJECT_DIR)
os.environ["DJANGO_SETTINGS_MODULE"] = "oj.settings"
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# --- Disable dotenv completely ---
if "DJANGO_SECRET_KEY" not in os.environ:
    os.environ["DJANGO_SECRET_KEY"] = "dummy-secret-for-export"
os.environ["DEBUG"] = "False"

# --- Initialize Django manually ---
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from django.apps import apps
from django.conf import settings

print("? Django loaded")
print("apps.ready:", apps.ready)
print("contenttypes in INSTALLED_APPS:", "django.contrib.contenttypes" in settings.INSTALLED_APPS)

# --- Real export logic ---
from problems.models import Problem, TestCase

DEST_ROOT = "/srv/judge/testcases"
os.makedirs(DEST_ROOT, exist_ok=True)

total = 0
for prob in Problem.objects.all():
    tcs = TestCase.objects.filter(problem=prob)
    if not tcs.exists():
        print(f"[SKIP] {prob.code}: no testcases.")
        continue

    in_dir = os.path.join(DEST_ROOT, prob.code, "in")
    out_dir = os.path.join(DEST_ROOT, prob.code, "out")
    os.makedirs(in_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    for i, tc in enumerate(tcs, start=1):
        with open(os.path.join(in_dir, f"{i}.inp"), "w", encoding="utf-8", errors="ignore") as f_in:
            f_in.write((tc.input_data or "").strip() + "\n")
        with open(os.path.join(out_dir, f"{i}.out"), "w", encoding="utf-8", errors="ignore") as f_out:
            f_out.write((tc.expected_output or "").strip() + "\n")

    print(f"[OK] {prob.code}: exported {tcs.count()} tests.")
    total += tcs.count()

print(f"=== ? Done. Total exported: {total} ===")
