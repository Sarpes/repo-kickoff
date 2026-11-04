"""Independent check of install_secret_gate.py: install into a fresh repo, then
commit through the real hook (as a user would) and assert refuse/accept.
Usage: python test_secret_gate.py   (exit 0 = pass)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

INSTALL = Path(__file__).with_name("install_secret_gate.py")
FAKE = "sk-ant-" + "api03-" + "x" * 30  # assembled at runtime

cases = [  # (file, content, should_commit)
    ("settings.py", f'API_KEY = "{FAKE}"\n', False),
    ("db.py", 'password = "hunter2hunter2"\n', False),  # planted test secret, secret-gate: allow
    (".env", "A=1\n", False),
    ("my_secret_gate.py", 'token = "abcdef123456"\n', False),  # only .githooks/secret_gate.py is exempt, secret-gate: allow
    ("janus_secrets.bat", "set A=1\n", False),  # secrets file by name
    ("db_ok.py", 'password = os.environ["DB_PASSWORD"]\nurl = "postgres://$USER"\n', True),
    ("doc.md", 'example: password = "changeme123"  # secret-gate: allow\n', True),  # secret-gate: allow
    ("test_secret_helpers.py", "def check():\n    return True\n", True),  # "secret" in a .py name is not a secrets file
    (".env.example", "A=\n", True),
]
fails = 0
with tempfile.TemporaryDirectory() as d:
    repo = Path(d)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    r = subprocess.run([sys.executable, "-I", str(INSTALL), str(repo)], capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        sys.exit(1)
    for name, content, should in cases:
        (repo / name).write_text(content, encoding="utf-8")
        g = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                      capture_output=True, text=True)
        g("add", "-f", name)
        ok = g("commit", "-qm", name).returncode == 0
        if not ok:
            g("reset", "-q", name)
        good = ok == should
        fails += not good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: {'committed' if ok else 'refused'} (expected {'commit' if should else 'refuse'})")
    attrs = (repo / ".gitattributes").read_text(encoding="utf-8")
    good = ".githooks/* text eol=lf" in attrs
    fails += not good
    print(f"  {'PASS' if good else 'FAIL'}  .gitattributes keeps hooks LF")
# The gate (installed into repos) and audit_repo.py must look for the same things.
# Compare the COMPILED patterns: the gate's are built by running the pattern lines of
# the gate source that install_secret_gate.py writes; audit_repo's by importing it.
import importlib.util  # noqa: E402


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, f"cannot load {path}"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


installer = load(INSTALL, "installer_under_test")
audit = load(INSTALL.with_name("audit_repo.py"), "audit_under_test")
gate_defs = installer.GATE.split("\ngit = lambda", 1)[0]     # imports + NAME / SAFE_NAME / TEXT only
gate = {}
exec(gate_defs, gate)
same = (gate["NAME"].pattern, gate["NAME"].flags) == (audit.SECRET_NAME.pattern, audit.SECRET_NAME.flags) and \
    (gate["TEXT"].pattern, gate["TEXT"].flags) == (audit.SECRET_TEXT.pattern, audit.SECRET_TEXT.flags)
fails += not same
print(f"  {'PASS' if same else 'FAIL'}  gate and audit_repo.py use identical secret patterns")
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
