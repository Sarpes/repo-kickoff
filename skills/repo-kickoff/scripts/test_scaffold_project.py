"""Test of scaffold_project.py: skeleton folders and a registry entry, always in temp dirs.
Never touches the real registry: CLAUDE_REGISTRY points at a temp file in every run.
Usage: python test_scaffold_project.py   (exit 0 = pass)
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT = Path(__file__).with_name("scaffold_project.py")
FOLDERS = ["handovers", "architecture", "guides", "artifacts", "archive"]
fails = 0


def check(name, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails += 1


def run(args, registry):
    env = dict(os.environ)
    if registry is None:
        env.pop("CLAUDE_REGISTRY", None)
    else:
        env["CLAUDE_REGISTRY"] = str(registry)
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", env=env)


with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    reg = d / "projects.yaml"
    reg.write_text("projects:\n  - id: existing\n    path: '/tmp/existing'\n", encoding="utf-8")
    proj = d / "demo-app"

    r = run([str(proj), "--id", "demo-app", "--co-author", "claude"], reg)
    check("exit 0 on a new project", r.returncode == 0)
    for f in FOLDERS:
        check(f"docs/{f}/.gitkeep exists", (proj / "docs" / f / ".gitkeep").is_file())
    text = reg.read_text(encoding="utf-8")
    check("existing registry entry kept", "- id: existing" in text)
    check("entry has id", "- id: demo-app" in text)
    check("entry has path", f"path: '{proj}'" in text)
    check("entry has status active", "status: active" in text)
    check("entry has co_author claude", "co_author: claude" in text)

    r = run([str(proj), "--id", "demo-app", "--co-author", "claude"], reg)
    check("duplicate id refused", r.returncode != 0)
    check("registry unchanged after refusal", reg.read_text(encoding="utf-8") == text)

    keep = proj / "docs" / "guides" / "note.md"
    keep.write_text("mine\n", encoding="utf-8")
    other = d / "second"
    r = run([str(other), "--id", "second", "--co-author", "none"], reg)
    check("co_author none recorded", "co_author: none" in reg.read_text(encoding="utf-8"))
    check("existing files never touched", keep.read_text(encoding="utf-8") == "mine\n")

    r = run([str(d / "x"), "--id", "Bad_Name", "--co-author", "claude"], reg)
    check("non-kebab id refused", r.returncode != 0 and not (d / "x").exists())
    r = run([str(d / "y"), "--id", "y", "--co-author", "maybe"], reg)
    check("co_author outside claude|none refused", r.returncode != 0 and not (d / "y").exists())
    r = run([str(d / "z"), "--id", "z"], reg)
    check("co_author is required (must be asked)", r.returncode != 0 and not (d / "z").exists())

    r = run([str(d / "w"), "--id", "w", "--co-author", "claude"], d / "missing" / "none.yaml")
    check("missing registry file refused, no folders made", r.returncode != 0 and not (d / "w").exists())

    r = run([str(d / "v"), "--id", "v", "--co-author", "claude", "--no-registry"], None)
    check("--no-registry makes folders without any registry", r.returncode == 0 and (d / "v" / "docs" / "archive" / ".gitkeep").is_file())

    r = run(["--print-registry-path"], reg)
    check("registry path comes from CLAUDE_REGISTRY", r.stdout.strip() == str(reg))
    r = run(["--print-registry-path"], None)
    check("default registry path is the workbench one", r.stdout.strip().endswith("registry" + chr(92) + "projects.yaml"))

print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
