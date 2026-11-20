"""Upload the built wheels and the sdist for this release.

Two details are load-bearing.

The sdist has to be in the list. This script used to glob only
``dist/tree_sitter_opencl-*.whl``, so every release went up wheels-only and
``pip install tree-sitter-opencl`` from source failed with "no matching
distribution" on any platform without a wheel -- which is every non-Windows
one. PyGPGPU depends on this package, so that gap blocked it too.

The filename must use underscores, not hyphens. PyPI rejects
``tree-sitter-opencl-0.0.4.tar.gz`` with ``400 Filename ... is invalid, should
be 'tree_sitter_opencl-0.0.4.tar.gz'``; setuptools >= 69 normalizes the name
itself, so an sdist built by an older setuptools is renamed here rather than
uploaded under a name the server refuses.

``--disable-progress-bar`` keeps twine from drawing its progress bar through
rich: on a GBK console that renderer raises UnicodeEncodeError mid-upload and
the process dies with a traceback after the bytes have already been sent.
"""

import glob
import os
import subprocess
import sys

DIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")


def artifacts() -> list[str]:
    wheels = sorted(glob.glob(os.path.join(DIST, "tree_sitter_opencl-*.whl")))
    sdists = {}
    for path in sorted(glob.glob(os.path.join(DIST, "*.tar.gz"))):
        name = os.path.basename(path)
        if name.startswith("tree-sitter-opencl-"):
            # An sdist built before setuptools normalized the name; rename it so
            # PyPI accepts the upload instead of answering 400. The rename never
            # overwrites a normalized build already in dist/: that one may be the
            # artifact a previous run published, and replacing it would leave the
            # checkout holding a different file from the one on PyPI.
            renamed = os.path.join(DIST, name.replace("tree-sitter-opencl-", "tree_sitter_opencl-", 1))
            if not os.path.exists(renamed):
                os.replace(path, renamed)
                path = renamed
            else:
                print("skipping superseded", name)
                continue
        # One sdist per version: a stale hyphenated build and its normalized
        # replacement describe the same release, and only one can be uploaded.
        sdists.setdefault(name, path)
    return wheels + [path for path in sdists.values() if os.path.exists(path)]


def main() -> int:
    files = artifacts()
    if not files:
        print("nothing to upload: dist/ holds no wheel or sdist")
        return 1
    for path in files:
        print(os.path.basename(path))
    return subprocess.call(
        [sys.executable, "-m", "twine", "upload", "--disable-progress-bar", *files]
    )


if __name__ == "__main__":
    sys.exit(main())
