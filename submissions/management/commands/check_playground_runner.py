import getpass
import os
import shutil
import subprocess

from django.core.management.base import BaseCommand

from judge.playground import (
    CPP_IMAGE,
    PYTHON_IMAGE,
    PlaygroundSystemError,
    run_playground,
    runner_health,
)


class Command(BaseCommand):
    help = "Check Docker access, playground images, compilation, execution and timeout"

    def report_check(self, label, callback):
        try:
            ok, detail = callback()
        except Exception as exc:
            ok, detail = False, str(exc)
        style = self.style.SUCCESS if ok else self.style.ERROR
        self.stdout.write(style(f"{'OK  ' if ok else 'FAIL'} {label}: {detail}"))
        return ok

    def handle(self, *args, **options):
        self.stdout.write(f"Service user: {getpass.getuser()} (uid={os.getuid()}, gid={os.getgid()})")
        self.report_check("Docker CLI", lambda: (bool(shutil.which("docker")), shutil.which("docker") or "not found"))

        def daemon():
            proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=10)
            return proc.returncode == 0, (proc.stderr or proc.stdout).strip()[-500:]
        self.report_check("Docker daemon permission", daemon)

        for label, image in (("C++ image", CPP_IMAGE), ("Python image", PYTHON_IMAGE)):
            def image_check(image=image):
                proc = subprocess.run(["docker", "image", "inspect", image], capture_output=True, text=True, timeout=10)
                return proc.returncode == 0, image if proc.returncode == 0 else (proc.stderr.strip() or "not found")
            self.report_check(label, image_check)

        healthy, detail = runner_health()
        if not healthy:
            self.stdout.write(self.style.WARNING(f"Runner tests skipped: {detail}"))
            self.stdout.write("Build images:")
            self.stdout.write("  docker build -t judge-cpp -f docker/playground/cpp/Dockerfile .")
            self.stdout.write("  docker build -t judge-py -f docker/playground/python/Dockerfile .")
            self.stdout.write("Permission (then re-login/restart service): sudo usermod -aG docker <service-user>")
            return

        cases = [
            ("C++ hello", "cpp17", '#include <iostream>\nint main(){std::cout<<"hello";}', "", "OK"),
            ("C++ compile error", "cpp17", "int main(){ return 0 }", "", "CE"),
            ("Python hello", "python", 'print("hello")', "", "OK"),
            ("Timeout", "cpp17", "int main(){while(true){}}", "", "TLE"),
        ]
        for label, language, source, stdin, expected in cases:
            def execute(language=language, source=source, stdin=stdin, expected=expected):
                try:
                    result = run_playground(language, source, stdin, time_limit=.5)
                    return result.status == expected, f"status={result.status} time={result.time_ms}ms"
                except PlaygroundSystemError as exc:
                    return False, str(exc)
            self.report_check(label, execute)
