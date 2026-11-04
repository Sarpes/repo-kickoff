"""Pin a Python project's dependencies to the versions it actually ran with.

Run it with the project's own interpreter (the venv the tests passed in):
    <venv>/Scripts/python scripts/pin_requirements.py <repo> [--write]

Scans every .py file git would track (respects .gitignore, works before the first
commit), splits imports into runtime and dev (files under tests/, test_*.py,
conftest.py), looks up the installed version of each in THIS interpreter and
prints (or with --write writes) requirements.txt, requirements-dev.txt and
.python-version. Exit 1 if an imported package is not installed here.
"""
import ast
import datetime as dt
import importlib.metadata as md
import platform
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# One mapping for both scripts: import name -> distribution, namespace packages by module prefix.
sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I leaves the script folder off sys.path
from audit_repo import KNOWN, NAMESPACE, import_key  # noqa: E402


def py_files(repo):
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return [f for f in out.split("\0") if f.endswith(".py")]


def is_dev(path):
    p = Path(path)
    return "tests" in p.parts or "test" in p.parts or p.name.startswith("test_") or p.name == "conftest.py"


def scan(repo, files):
    local = {Path(f).parts[0].removesuffix(".py") for f in files} | {Path(f).stem for f in files}
    runtime, dev = {}, {}
    for f in files:
        tree = ast.parse((repo / f).read_text(encoding="utf-8", errors="replace"))
        for node in ast.walk(tree):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module else []
            for n in names:
                top = n.split(".")[0]
                if top in sys.stdlib_module_names or top in local or top == "__future__":
                    continue
                (dev if is_dev(f) else runtime).setdefault(import_key(n), f)
    return runtime, dev


def resolve(tops):
    dist_of = {k: v[0] for k, v in md.packages_distributions().items() if v}
    pins, missing = {}, []
    for top in sorted(tops):
        dist = KNOWN.get(top) or (top if top in NAMESPACE.values() else dist_of.get(top)) or top
        try:
            pins[dist] = md.version(dist)
        except md.PackageNotFoundError:
            missing.append(f"{top} (distribution `{dist}`)")
    return pins, missing


def main():
    args = [a for a in sys.argv[1:] if a != "--write"]
    if len(args) != 1:
        print(__doc__)
        sys.exit(2)
    repo = Path(args[0]).resolve()
    runtime, dev = scan(repo, py_files(repo))
    run_pins, miss1 = resolve(runtime)
    dev_pins, miss2 = resolve(set(dev) - set(runtime))
    if miss1 or miss2:
        print(f"Not installed in {sys.executable}: " + ", ".join(miss1 + miss2))
        print("Run this with the project's venv interpreter, after installing and testing.")
        sys.exit(1)
    ver = platform.python_version()
    head = (f"# Pinned by pin_requirements.py on {dt.date.today()} with Python {ver}.\n"
            f"# These are the exact versions the code and tests ran with. Regenerate after upgrading.\n")
    files = {
        "requirements.txt": head + "".join(f"{d}=={v}\n" for d, v in sorted(run_pins.items(), key=lambda x: x[0].lower())),
        "requirements-dev.txt": head + "-r requirements.txt\n" + "".join(f"{d}=={v}\n" for d, v in sorted(dev_pins.items(), key=lambda x: x[0].lower())),
    }
    if not (repo / ".python-version").exists():
        files[".python-version"] = ".".join(ver.split(".")[:2]) + "\n"
    if not dev_pins:
        files.pop("requirements-dev.txt")
    for name, text in files.items():
        print(f"--- {name}\n{text}")
    if "--write" in sys.argv:
        for name, text in files.items():
            (repo / name).write_text(text, encoding="utf-8", newline="\n")
        print("WRITTEN: " + ", ".join(files))
    else:
        print("dry run — pass --write to write")


if __name__ == "__main__":
    main()
