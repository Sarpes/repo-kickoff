"""Red/green test for audit_repo.py: a throwaway repo with planted defects must
produce each expected finding; a clean variant must produce none of them.
Usage: python test_audit_repo.py   (exit 0 = all checks pass)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TOOL = Path(__file__).with_name("audit_repo.py")
FAKE_TOKEN = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"  # built at runtime, not a real token


def make_repo(root: Path, dirty: bool):
    (root / "app").mkdir()
    (root / "app" / "main.py").write_text(
        "import os\nimport requests\nimport yaml\nfrom app import util\n\nprint(requests, yaml, util, os)\n", encoding="utf-8")
    (root / "app" / "util.py").write_text("X = 1\n", encoding="utf-8")
    reqs = "requests==2.33.0\n" if dirty else "requests==2.33.0\npyyaml==6.0.2\n"
    (root / "requirements.txt").write_text(reqs, encoding="utf-8")
    # a test-only import satisfied by the dev file must NOT be reported
    (root / "tests").mkdir()
    (root / "tests" / "test_main.py").write_text("import pytest\n", encoding="utf-8")
    (root / "requirements-dev.txt").write_text("-r requirements.txt\npytest==8.4.2\n", encoding="utf-8")
    # the project's own package in a src/ layout, imported by its tests, is first-party, not a missing dependency
    (root / "src" / "call_pipeline").mkdir(parents=True)
    (root / "src" / "call_pipeline" / "__init__.py").write_text("", encoding="utf-8")
    (root / "src" / "call_pipeline" / "core.py").write_text("X = 1\n", encoding="utf-8")
    (root / "tests" / "test_core.py").write_text("from call_pipeline import core\n", encoding="utf-8")
    # a second environment (e.g. a Docker worker) with its own requirements file in a subfolder;
    # import names differ from package names and the packages need not be installed here
    (root / "worker").mkdir()
    (root / "worker" / "job.py").write_text("import docx\nfrom fpdf import FPDF\nfrom google.oauth2 import service_account\n", encoding="utf-8")
    if not dirty:
        (root / "worker" / "requirements.txt").write_text("python-docx==1.1.2\nfpdf2==2.8.1\ngoogle-auth==2.40.0\n", encoding="utf-8")
    if not dirty:
        (root.parent / f"{root.name}-internal").mkdir()   # the private companion next to the repo
        (root / ".python-version").write_text("3.13\n", encoding="utf-8")
        # files the skill itself creates must not be reported as secrets
        (root / ".githooks").mkdir()
        (root / ".githooks" / "secret_gate.py").write_text("NAME = 'x'\n", encoding="utf-8")
        (root / ".env.example").write_text("API_KEY=\n", encoding="utf-8")
    readme = "# Demo\n\nEntry point: `app/main.py:3`.\n"
    readme += "Helper: `app/util.py:40`.\n" if dirty else "Helper: `app/util.py:1`.\n"
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / ".gitignore").write_text(".env\n", encoding="utf-8")
    cfg = 'db_password = "$DB_PASSWORD"\n' + 'api_key = os.environ["EXAMPLE_API_KEY"]\ntoken = compute_token_for_request(user)\n'
    if dirty:
        cfg += f'password = "hunter22"\ntoken = "{FAKE_TOKEN}"\n'  # planted test secret, secret-gate: allow
        (root / ".env").write_text("A=1\n", encoding="utf-8")
        (root / "UsersExampleUser.env").write_text("A=1\n", encoding="utf-8")  # name ends in .env
        cfg += "EXAMPLE_API_KEY=" + "0123456789abcdef" * 2 + "\n"  # unquoted env-style, obviously fake
    (root / "config.py").write_text(cfg, encoding="utf-8")
    run = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)
    run("init", "-q")
    run("add", ".")
    if dirty:
        run("add", "-f", ".env")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "fixture")
    # Deleting a file does not remove it from git history: anyone who clones can still read it.
    # dirty: a token and a secrets-named file committed, then deleted. clean: a harmless file, same path of life.
    old = {"old_settings.py": f'token = "{FAKE_TOKEN}"\n', "backup.env": "A=1\n"} if dirty \
        else {"old_notes.py": 'token = compute_token_for_request(user)\n'}
    for name, content in old.items():
        (root / name).write_text(content, encoding="utf-8")
        run("add", "-f", name)
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "add old files")
    run("rm", "-q", *old)
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "remove old files")
    if dirty:  # a secret that is still in the current file is reported once (IGN), not again as history
        (root / "config.py").write_text(cfg + "# edited\n", encoding="utf-8")
        run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qam", "edit config")


def audit(root: Path):
    r = subprocess.run([sys.executable, "-I", str(TOOL), str(root)], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


EXPECT_DIRTY = [
    ("missing requirement", "imports `yaml` but no requirements file or pyproject lists `pyyaml`"),
    ("no python version", "no Python version stated"),
    ("namespace package mapped by its full module", "lists `google-auth`"),
    ("import name != package name, not installed", "lists `python-docx`"),
    ("line out of range", "`app/util.py:40` but the file has 1 lines"),
    ("plain password", "config.py:4  line looks like a secret"),
    ("github token", "config.py:5  line looks like a secret"),
    ("ignored but tracked", ".env  tracked although .gitignore ignores it"),
    ("secret file name", ".env  tracked file name looks like a secret"),
    ("name ending in .env", "UsersExampleUser.env  tracked file name looks like a secret"),
    ("unquoted env-style value", "config.py:6  line looks like a secret"),
    ("secret line only in git history", "HIST  old_settings.py:1"),
    ("secret file name only in git history", "HIST  backup.env"),
    ("no private companion next to the repo", "CMP  repo  no private companion folder dirty-internal"),
]
FORBID_CLEAN = ["config.py:1", "looks like a secret", "lists `", "but the file has", "`pytest`", "no Python version",
                "`call_pipeline`", "HIST", "CMP"]

fails = 0
with tempfile.TemporaryDirectory() as d:
    dirty, clean = Path(d, "dirty"), Path(d, "clean")
    dirty.mkdir()
    clean.mkdir()
    make_repo(dirty, True)
    make_repo(clean, False)
    code, out = audit(dirty)
    print(f"dirty repo: exit {code}")
    for label, needle in EXPECT_DIRTY:
        ok = needle in out
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  catches {label}")
    ok = "HIST  config.py" not in out
    fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  a secret still in the current file is not reported again as history")
    if code != 1:
        fails += 1
        print("  FAIL  exit code should be 1")
    code, out = audit(clean)
    print(f"clean repo: exit {code}")
    for needle in FORBID_CLEAN:
        ok = needle not in out
        fails += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  no '{needle}'")
    if code != 0:
        fails += 1
        print("  FAIL  exit code should be 0\n" + out)
    # a companion repo itself needs no companion of its own
    comp = Path(d, "notes-internal")
    comp.mkdir()
    (comp / "README.md").write_text("# Notes\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(comp), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(comp), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(comp), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"], check=True)
    code, out = audit(comp)
    ok = "CMP" not in out
    fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  a *-internal repo is not asked for a companion")
print(f"{'ALL PASS' if not fails else f'{fails} FAILED'}")
sys.exit(1 if fails else 0)
