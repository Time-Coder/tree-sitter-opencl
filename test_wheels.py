"""Install the built abi3 wheels into every interpreter and parse a kernel.

This is the verify-only half of ``build_matrix.py`` -- the same check, against
what is already in ``dist/`` instead of rebuilding first.

The wheel is one file per architecture, so the interesting question is not "is
there a wheel for this interpreter" (with a ``cp37-abi3`` tag there never is one)
but "does the one wheel load here". Every CPython from 3.7 to 3.15, on both
architectures, is asked that.
"""

import glob
import os
import shutil
import subprocess
import sys
import zipfile

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
ROOT = os.path.dirname(os.path.abspath(__file__))

VERSIONS = ["37", "38", "39", "310", "311", "312", "313", "314", "315"]
ARCHES = [("win_amd64", ""), ("win32", "-32")]

CHECK = (
    "import sys, struct, tree_sitter as ts, tree_sitter_opencl as o;"
    "l = o.language();"
    "p = ts.Parser() if hasattr(ts.Parser, 'set_language') else ts.Parser(l);"
    "p.set_language(l) if hasattr(ts.Parser, 'set_language') else None;"
    "t = p.parse(b'__kernel void k(__global float*o){o[0]=1.0f;}');"
    "assert t.root_node.type == 'translation_unit', t.root_node.type;"
    "assert not t.root_node.has_error, 'parse error';"
    "print(sys.version.split()[0], struct.calcsize('P')*8, 'bits', 'v'+o.__version__)"
)


def wheel_for(arch: str) -> str | None:
    """Newest abi3 wheel for one architecture.

    The glob asks for ``abi3`` rather than for an interpreter tag: a wheel named
    ``cpXXX-cpXXXm`` is the old per-version build, and installing that would make
    this script pass while proving nothing about the single-wheel claim.
    """
    matches = glob.glob(os.path.join(DIST, "tree_sitter_opencl-*-abi3-%s.whl" % arch))
    if not matches:
        return None

    def version_key(path: str) -> tuple:
        name = os.path.basename(path)
        version = name.split("-", 1)[1].rsplit("-", 3)[0]
        return tuple(int(part) for part in version.split(".") if part.isdigit())

    return sorted(matches, key=version_key)[-1]


def main() -> int:
    failures = []
    for arch, suffix in ARCHES:
        wheel = wheel_for(arch)
        if wheel is None:
            print("no abi3 wheel for %s in dist/; run build_matrix.py first" % arch)
            failures.append((arch, "no wheel"))
            continue
        print("=== %s -> %s ===" % (arch, os.path.basename(wheel)))

        for version in VERSIONS:
            interpreter = r"D:\Python\%s%s\python.exe" % (version, suffix)
            if not os.path.exists(interpreter):
                failures.append((interpreter, "missing interpreter"))
                continue

            # tree-sitter 0.26 has no 3.7 wheel; 0.20.4 is what that line runs.
            pin = "tree-sitter==0.20.4" if version == "37" else "tree-sitter>=0.23"
            installed = subprocess.run(
                [interpreter, "-m", "pip", "install", "--quiet",
                 "--disable-pip-version-check", pin],
                capture_output=True, text=True,
            )

            pythonpath = None
            if installed.returncode != 0:
                # Python 3.8's bundled pip cannot reach PyPI on this machine (its
                # vendored urllib3 fails TLS with "check_hostname requires
                # server_hostname"), and upgrading pip is the very thing that
                # cannot be done. Both 3.8 interpreters already have tree-sitter,
                # so the wheel is unpacked onto PYTHONPATH instead -- the import
                # still exercises the same `_binding.pyd`, which is the subject.
                already = subprocess.run([interpreter, "-c", "import tree_sitter"],
                                         capture_output=True, text=True)
                if already.returncode != 0:
                    failures.append((interpreter, installed.stderr.strip()[-300:]))
                    continue
                print("    (pip unusable; using the interpreter directly)")
                pythonpath = os.path.join(ROOT, "build", "unpacked-%s" % arch)
                shutil.rmtree(pythonpath, ignore_errors=True)
                os.makedirs(pythonpath)
                with zipfile.ZipFile(wheel) as archive:
                    archive.extractall(pythonpath)
                python = interpreter
            else:
                installed = subprocess.run(
                    [interpreter, "-m", "pip", "install", "--quiet",
                     "--disable-pip-version-check", "--force-reinstall", "--no-deps",
                     wheel],
                    capture_output=True, text=True,
                )
                if installed.returncode != 0:
                    failures.append((interpreter, installed.stderr.strip()[-300:]))
                    continue
                python = interpreter

            environment = dict(os.environ)
            if pythonpath:
                environment["PYTHONPATH"] = pythonpath
            proc = subprocess.run([python, "-c", CHECK], capture_output=True,
                                  text=True, env=environment)
            if proc.returncode != 0:
                failures.append((interpreter, (proc.stderr or proc.stdout).strip()[-300:]))
                print("  %-34s FAIL" % interpreter)
            else:
                print("  ok  %-34s %s" % (interpreter, proc.stdout.strip()))

    if failures:
        print("\n=== failures ===")
        for interpreter, message in failures:
            print(interpreter, "->", message)
        return 1
    print("\nevery interpreter loaded the same abi3 wheel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
