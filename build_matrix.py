"""Build one abi3 wheel per architecture, then install it on every interpreter.

The extension targets the limited API (``Py_LIMITED_API = 0x03070000``) and is
tagged ``cp37-abi3``, so a single wheel per platform installs on CPython 3.7
through 3.15. This script used to build eighteen wheels -- one per interpreter
and architecture -- because ``bdist_wheel`` was invoked without
``--py-limited-api``; the tag is now an option in ``setup.py``, so a plain build
already produces abi3 and the matrix collapses to two builds.

The interpreters are still all exercised, which is the part that matters: the
wheel is one file but it has to *load* on every interpreter it claims. Each one
gets the wheel installed into a throwaway venv and parses a kernel. That check
is the reason the script exists, not the build.
"""

import glob
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
PACKAGE = "tree_sitter_opencl"
DIST_NAME = "tree_sitter_opencl"

# (interpreter, architecture) pairs to verify. The abi3 wheel is one per
# architecture, and each is installed on every CPython version for that
# architecture -- the tag claims that, so the test proves it.
ARCHITECTURES = [("win_amd64", ""), ("win32", "-32")]
VERSIONS = ["37", "38", "39", "310", "311", "312", "313", "314", "315"]

CHECK = (
    "import sys, tree_sitter, tree_sitter_opencl as o;"
    "l = o.language();"
    # The parser constructor moved in 0.23; the check has to pass on both.
    "p = tree_sitter.Parser() if hasattr(tree_sitter.Parser, 'set_language') else tree_sitter.Parser(l);"
    "p.set_language(l) if hasattr(tree_sitter.Parser, 'set_language') else None;"
    "t = p.parse(b'__kernel void k(__global float*o){o[0]=1.0f;}');"
    "assert t.root_node.type == 'translation_unit', t.root_node.type;"
    "assert not t.root_node.has_error, 'parse error';"
    "print(sys.version.split()[0], o.__version__)"
)


def build_sdist() -> str:
    """Build the sdist, by an interpreter whose setuptools normalises its name.

    PyPI rejects ``tree-sitter-opencl-0.0.5.tar.gz`` -- it wants the underscores
    -- and setuptools only started normalising the filename in 69. The 3.7
    interpreter is capped at 68.0.0, so an sdist built there is refused at
    upload time. The sdist compiles nothing, so which interpreter writes the
    tarball does not matter; what matters is that its setuptools is new enough.
    """
    dist = os.path.join(ROOT, "dist")
    interpreter = r"D:\Python\310\python.exe"
    version = subprocess.check_output(
        [interpreter, "-c",
         "import setuptools; print(setuptools.__version__)"],
        text=True,
    ).strip()
    major, minor = (int(part) for part in version.split(".")[:2])
    if (major, minor) < (69, 0):
        raise SystemExit(
            "setuptools %s on %s still writes a hyphenated sdist name that PyPI"
            " rejects; install setuptools>=69 there" % (version, interpreter)
        )
    subprocess.check_call([interpreter, "setup.py", "sdist", "--dist-dir", dist],
                          cwd=ROOT)
    built = sorted(glob.glob(os.path.join(dist, "*.tar.gz")), key=os.path.getmtime)
    if not built:
        raise SystemExit("no sdist in dist/")
    return built[-1]


def build(arch_tag: str) -> str:
    """Build the abi3 wheel for one architecture with its own interpreter.

    The wheel is built by the *lowest* supported interpreter on purpose: the
    extension is compiled against the limited API floor, and building it on 3.7
    proves the floor is real instead of assuming it.

    ``build/`` is removed first. setuptools caches compiled objects there and
    decides whether to recompile by timestamp, so a macro change alone (removing
    ``TREE_SITTER_HIDE_SYMBOLS`` cost an afternoon of exactly this) leaves the
    old ``parser.obj`` in the wheel -- the build is green and the artefact is
    stale.
    """
    interpreter = r"D:\Python\37%s\python.exe" % ("" if arch_tag == "win_amd64" else "-32")
    dist = os.path.join(ROOT, "dist")
    shutil.rmtree(os.path.join(ROOT, "build"), ignore_errors=True)
    subprocess.check_call(
        [interpreter, "setup.py", "bdist_wheel", "--dist-dir", dist], cwd=ROOT,
    )
    built = glob.glob(os.path.join(dist, "*%s.whl" % arch_tag))
    if not built:
        raise SystemExit("no %s wheel in dist/" % arch_tag)
    return max(built, key=os.path.getmtime)


def _interpreter_has(python: str, module: str) -> bool:
    """Is ``module`` importable by ``python`` already?"""
    result = subprocess.run([python, "-c", "import %s" % module],
                            capture_output=True, text=True)
    return result.returncode == 0


def verify(wheel: str, arch_tag: str) -> list:
    """Load ``wheel`` on every interpreter for one architecture and parse."""
    failures = []
    workdir = os.path.join(ROOT, "build", "verify-%s" % arch_tag)
    shutil.rmtree(workdir, ignore_errors=True)
    os.makedirs(workdir)

    for version in VERSIONS:
        suffix = "" if arch_tag == "win_amd64" else "-32"
        interpreter = r"D:\Python\%s%s\python.exe" % (version, suffix)
        if not os.path.exists(interpreter):
            failures.append((interpreter, "missing interpreter"))
            continue

        venv = os.path.join(workdir, "v%s" % version)
        subprocess.check_call([interpreter, "-m", "venv", venv])
        python = os.path.join(venv, "Scripts", "python.exe")

        # tree-sitter 0.26 has no 3.7 wheel; 0.20.4 is what that line runs. The
        # grammar has to load on both ends of the range, so both are installed.
        tree_sitter_pin = "tree-sitter==0.20.4" if version == "37" else "tree-sitter>=0.23"
        installed = subprocess.run(
            [python, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
             tree_sitter_pin],
            capture_output=True, text=True,
        )

        pythonpath = None
        if installed.returncode != 0:
            # Python 3.8's bundled pip cannot reach PyPI on this machine: its
            # vendored urllib3 fails TLS with "check_hostname requires
            # server_hostname", and upgrading pip is the very thing that cannot
            # be done. A pip-only check would report a broken *interpreter* as a
            # broken *wheel*. Both 3.8 interpreters already have tree-sitter, so
            # the check falls back to them directly: the wheel is unpacked and
            # put on PYTHONPATH, and the import still exercises the same
            # `_binding.pyd`, which is what this verifies.
            if not _interpreter_has(interpreter, "tree_sitter"):
                failures.append((interpreter, installed.stderr.strip()[-300:]))
                continue
            print("    (pip unusable for this interpreter; using it directly)")
            python = interpreter
            pythonpath = os.path.join(ROOT, "build", "unpacked", os.path.basename(wheel))
            shutil.rmtree(pythonpath, ignore_errors=True)
            os.makedirs(pythonpath, exist_ok=True)
            with zipfile.ZipFile(wheel) as archive:
                archive.extractall(pythonpath)
        else:
            installed = subprocess.run(
                [python, "-m", "pip", "install", "--quiet", "--disable-pip-version-check",
                 "--force-reinstall", "--no-deps", wheel],
                capture_output=True, text=True,
            )
            if installed.returncode != 0:
                failures.append((interpreter, installed.stderr.strip()[-300:]))
                continue

        environment = dict(os.environ)
        if pythonpath:
            environment["PYTHONPATH"] = pythonpath
        result = subprocess.run([python, "-c", CHECK], capture_output=True, text=True,
                                env=environment)
        if result.returncode != 0:
            failures.append((interpreter, (result.stderr or result.stdout).strip()[-300:]))
        else:
            print("  ok  %-34s %s" % (interpreter, result.stdout.strip()))

    return failures


def main() -> int:
    failures = []

    print("=== sdist ===")
    try:
        print("  sdist: %s" % os.path.basename(build_sdist()))
    except (subprocess.CalledProcessError, SystemExit) as error:
        failures.append(("sdist", str(error)))

    for arch_tag, _ in ARCHITECTURES:
        print("=== %s ===" % arch_tag)
        wheel = build(arch_tag)
        print("  wheel: %s" % os.path.basename(wheel))
        failures.extend(verify(wheel, arch_tag))

    print()
    wheels = sorted(glob.glob(os.path.join(ROOT, "dist", "*-abi3-*.whl")))
    print("%d abi3 wheel(s) in dist/: %s"
          % (len(wheels), ", ".join(os.path.basename(w) for w in wheels)))
    sdists = sorted(glob.glob(os.path.join(ROOT, "dist", "*.tar.gz")))
    print("%d sdist(s): %s"
          % (len(sdists), ", ".join(os.path.basename(s) for s in sdists)))
    # PyPI refuses a hyphenated sdist name, so check it here rather than at
    # upload time -- that failure has already happened once.
    for sdist in sdists:
        if "-" in os.path.basename(sdist)[:-len(".tar.gz")] and "_" not in os.path.basename(sdist):
            failures.append((sdist, "hyphenated sdist name; PyPI will reject it"))

    if failures:
        print("\n=== failures ===")
        for interpreter, message in failures:
            print(interpreter, "->", message)
        return 1
    print("every interpreter loaded the same wheel")
    return 0


if __name__ == "__main__":
    sys.exit(main())
