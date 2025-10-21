import subprocess, tempfile, os, textwrap, shlex

COMPILERS = {
    'cpp': {
        'src': 'main.cpp',
        'compile': lambda tmp, src: ["g++", src, "-O2", "-std=c++17", "-pipe", "-o", os.path.join(tmp, "main")],
        'run':      lambda tmp: [os.path.join(tmp, "main")],
    },
    'python': {
        'src': 'main.py',
        'compile': None,
        'run':      lambda tmp: ["python3", os.path.join(tmp, "main.py")],
    },
    'pypy': {
        'src': 'main.py',
        'compile': None,
        'run':      lambda tmp: ["pypy3", os.path.join(tmp, "main.py")],
    },
    'java': {
        'src': 'Main.java',
        'compile': lambda tmp, src: ["javac", src],
        'run':      lambda tmp: ["java", "-cp", tmp, "Main"],
    },
}


def run_program(language: str, source_code: str, input_data: str, time_limit: int = 5):
    if language not in COMPILERS:
        return ("Unsupported language", 0.0)
    cfg = COMPILERS[language]

    with tempfile.TemporaryDirectory() as tmp:
        src_path = os.path.join(tmp, cfg['src'])
        with open(src_path, 'w') as f:
            f.write(source_code)

        # compile if needed
        if cfg['compile']:
            try:
                c = subprocess.run(cfg['compile'](tmp, src_path), capture_output=True, text=True, timeout=30)
                if c.returncode != 0:
                    return ("Compilation Error:\n" + c.stderr, 0.0)
            except subprocess.TimeoutExpired:
                return ("Compilation Time Limit Exceeded", 0.0)

        # run
        try:
            r = subprocess.run(
                cfg['run'](tmp),
                input=input_data,
                capture_output=True,
                text=True,
                timeout=time_limit,
                env={"PYTHONUNBUFFERED":"1","JAVA_TOOL_OPTIONS":"-Xmx256m"},
            )
            if r.returncode != 0:
                return ("Runtime Error:\n" + r.stderr, 0.0)
            return (r.stdout, r.stderr)
        except subprocess.TimeoutExpired:
            return ("Time Limit Exceeded", 0.0)
