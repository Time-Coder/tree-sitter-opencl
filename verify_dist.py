import glob
import os
import sys
import zipfile

dist = sys.argv[1] if len(sys.argv) > 1 else "dist"
expect_versions = ["cp37", "cp38", "cp39", "cp310", "cp311", "cp312", "cp313", "cp314", "cp315"]
seen = set()
problems = []

for path in sorted(glob.glob(os.path.join(dist, "*.whl"))):
    name = os.path.basename(path)
    z = zipfile.ZipFile(path)
    wheel_meta = [n for n in z.namelist() if n.endswith(".dist-info/WHEEL")]
    tag = ""
    if wheel_meta:
        for line in z.read(wheel_meta[0]).decode().splitlines():
            if line.startswith("Tag:"):
                tag = line.split(":", 1)[1].strip()
    pyd = [n for n in z.namelist() if n.endswith(".pyd")]
    parts = name.split("-")
    pyver = parts[2]
    arch = parts[-1].replace(".whl", "")
    expect_arch_tag = "win32" if arch == "win32" else "win_amd64"
    ok = bool(pyd) and tag.startswith(pyver) and expect_arch_tag in tag
    if not ok:
        problems.append(name)
    seen.add((pyver, arch))
    print("%-52s tag=%-22s %s  %s" % (name, tag, len(pyd), pyd[0] if pyd else "NO .pyd"))

print()
missing = [(v, a) for v in expect_versions for a in ("win32", "win_amd64") if (v, a) not in seen]
print("wheels:", len(glob.glob(os.path.join(dist, "*.whl"))), "expected 18")
print("missing:", missing if missing else "none")
print("problems:", problems if problems else "none")
sys.exit(1 if (missing or problems) else 0)
