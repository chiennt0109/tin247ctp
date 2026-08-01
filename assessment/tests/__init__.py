"""Canonical assessment test discovery.

Some long-lived deployments retain untracked test modules after switching
branches.  Those modules exercise models and APIs that were deliberately
removed.  Keep discovery constrained to the test modules shipped by the
current package instead of importing obsolete filesystem debris.
"""

from importlib import import_module
from pathlib import Path


REMOVED_TEST_MODULES = {"test_demo_seed", "test_phase4_cleanup"}


def load_tests(loader, standard_tests, pattern):
    suite = loader.suiteClass()
    for path in sorted(Path(__file__).parent.glob("test_*.py")):
        if path.stem in REMOVED_TEST_MODULES:
            continue
        module = import_module(f"{__name__}.{path.stem}")
        suite.addTests(loader.loadTestsFromModule(module))
    return suite
