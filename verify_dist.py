"""Check the wheels in dist/ are the abi3 pair that replaced the 18-wheel matrix.

Three facts are checked, because each is a way the build can silently regress:

* **The tag must be ``cp37-abi3``.** A wheel tagged ``cp37-cp37m`` means
  ``bdist_wheel`` ran without ``--py-limited-api``, so it installs on 3.7 only and
  the single-wheel claim is false. That was the state of this repository before
  the option moved into ``setup.py``.
* **Each wheel must carry the compiled extension.** An abi3 tag on a wheel with
  no ``_binding.pyd`` would install everywhere and import nowhere.
* **Both architectures must be present.** One platform's wheel is the whole
  point: there should be exactly two, ``win_amd64`` and ``win32``, not eighteen.
"""

import glob
import os
import sys
import zipfile

dist = sys.argv[1] if len(sys.argv) > 1 else "dist"
expected_arches = {"win_amd64", "win32"}

wheels = sorted(glob.glob(os.path.join(dist, "*.whl")))
problems = []
seen = set()

for path in wheels:
    name = os.path.basename(path)
    archive = zipfile.ZipFile(path)
    wheel_meta = [n for n in archive.namelist() if n.endswith(".dist-info/WHEEL")]
    tags = []
    if wheel_meta:
        for line in archive.read(wheel_meta[0]).decode().splitlines():
            if line.startswith("Tag:"):
                tags.append(line.split(":", 1)[1].strip())

    extension = [n for n in archive.namelist() if n.endswith(".pyd") or n.endswith(".so")]
    arches = {tag.rsplit("-", 1)[-1] for tag in tags}
    seen |= arches

    problems_here = []
    if not all(tag.startswith("cp37-abi3-") for tag in tags) or not tags:
        problems_here.append("tag is not cp37-abi3 (%s)" % (tags or "none"))
    if not extension:
        problems_here.append("no compiled extension")
    if not arches <= expected_arches:
        problems_here.append("unexpected architecture %s" % sorted(arches))

    status = "ok" if not problems_here else "PROBLEM"
    print("%-52s %-22s %s %s"
          % (name, ",".join(tags) or "-", len(extension), status))
    if problems_here:
        problems.append((name, "; ".join(problems_here)))

print()
print("wheels: %d (expected 2: one per architecture, not one per interpreter)" % len(wheels))
missing = expected_arches - seen
print("missing architectures:", sorted(missing) if missing else "none")
print("problems:", problems if problems else "none")

if len(wheels) != 2:
    print("note: %d wheels -- the matrix should collapse to one per architecture" % len(wheels))

sys.exit(1 if (missing or problems) else 0)
