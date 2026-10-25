"""Install each built wheel into its matching interpreter and parse a kernel."""

import glob
import os
import subprocess
import sys

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")

VERSIONS = ["37", "38", "39", "310", "311", "312", "313", "314", "315"]
ARCHES = [("win_amd64", ""), ("win32", "-32")]

CHECK = (
    "import tree_sitter as ts, tree_sitter_opencl as o;"
    "l=o.language();"
    "p=ts.Parser() if hasattr(ts.Parser,'set_language') else ts.Parser(l);"
    "(hasattr(p,'set_language') and p.set_language(l)) or None;"
    "t=p.parse(b'__kernel void k(__global float*o){o[0]=1.0f;}');"
    "print('abi', getattr(l,'version',getattr(l,'abi_version','?')),"
    "'root', t.root_node.type, 'err', t.root_node.has_error)"
)


def wheel_for(ver: str, arch: str) -> str | None:
    matches = sorted(glob.glob(os.path.join(DIST, "tree_sitter_opencl-0.0.2-cp%s-*-%s.whl" % (ver, arch))))
    return matches[0] if matches else None


def main() -> int:
    failures = []
    for ver in VERSIONS:
        for arch, suffix in ARCHES:
            python = r"D:\Python\%s%s\python.exe" % (ver, suffix)
            if not os.path.exists(python):
                failures.append((python, "missing interpreter"))
                continue
            wheel = wheel_for(ver, arch)
            if wheel is None:
                failures.append((python, "no wheel"))
                continue
            # tree-sitter is only needed to exercise the grammar; install the
            # version that has wheels for that interpreter.
            install = subprocess.run(
                [python, "-m", "pip", "install", "--quiet", "--no-warn-script-location",
                 "--force-reinstall", "--no-deps", wheel],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            if install.returncode != 0:
                failures.append((python, install.stdout.decode("utf-8", "replace")[-300:]))
                continue
            proc = subprocess.run([python, "-c", CHECK], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output = proc.stdout.decode("utf-8", "replace").strip().splitlines()
            if proc.returncode != 0:
                failures.append((python, "\n".join(output[-3:])))
                print("%-34s FAIL %s" % (python, output[-1] if output else ""))
            else:
                print("%-34s %s" % (python, output[-1] if output else "ok"))

    if failures:
        print("\n=== failures ===")
        for python, message in failures:
            print(python, "->", message)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())