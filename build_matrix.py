"""Build tree-sitter-opencl wheels for CPython 3.7-3.15, 64- and 32-bit.

Runs `setup.py bdist_wheel` once per interpreter. The very first interpreter
also produces the sdist so PyPI gets a source distribution alongside the
binary wheels.
"""

import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

INTERPRETERS = [
    r"D:\Python\37\python.exe",
    r"D:\Python\38\python.exe",
    r"D:\Python\39\python.exe",
    r"D:\Python\310\python.exe",
    r"D:\Python\311\python.exe",
    r"D:\Python\312\python.exe",
    r"D:\Python\313\python.exe",
    r"D:\Python\314\python.exe",
    r"D:\Python\315\python.exe",
    r"D:\Python\37-32\python.exe",
    r"D:\Python\38-32\python.exe",
    r"D:\Python\39-32\python.exe",
    r"D:\Python\310-32\python.exe",
    r"D:\Python\311-32\python.exe",
    r"D:\Python\312-32\python.exe",
    r"D:\Python\313-32\python.exe",
    r"D:\Python\314-32\python.exe",
    r"D:\Python\315-32\python.exe",
]


def main() -> int:
    dist = os.path.join(ROOT, "dist")
    shutil.rmtree(dist, ignore_errors=True)
    shutil.rmtree(os.path.join(ROOT, "build"), ignore_errors=True)
    os.makedirs(dist, exist_ok=True)

    failures = []
    for index, python in enumerate(INTERPRETERS):
        if not os.path.exists(python):
            failures.append((python, "missing interpreter"))
            continue
        commands = ["sdist", "bdist_wheel"] if index == 0 else ["bdist_wheel"]
        # A stale build/ directory would leak objects compiled for the previous
        # interpreter into this wheel, so it is removed before every build.
        shutil.rmtree(os.path.join(ROOT, "build"), ignore_errors=True)
        result = subprocess.run(
            [python, "setup.py"] + commands,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if result.returncode != 0:
            tail = result.stdout.decode("utf-8", "replace").strip().splitlines()[-6:]
            failures.append((python, "\n".join(tail)))
            print("FAILED:", python)
        else:
            print("ok:", python)

    wheels = sorted(f for f in os.listdir(dist) if f.endswith((".whl", ".tar.gz")))
    print("\n=== %d artifacts ===" % len(wheels))
    for name in wheels:
        print(name)

    if failures:
        print("\n=== failures ===")
        for python, message in failures:
            print(python, "->", message)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())