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

with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    for quote in ('"', "'"):
        reg = d / f"q{ord(quote)}.yaml"
        reg.write_text(f"projects:\n  - id: {quote}taken{quote}\n    status: active\n", encoding="utf-8")
        before = reg.read_text(encoding="utf-8")
        r = run([str(d / f"t{ord(quote)}"), "--id", "taken", "--co-author", "claude"], reg)
        check(f"quoted id ({quote}) counts as duplicate", r.returncode != 0 and not (d / f"t{ord(quote)}").exists())
        check(f"registry unchanged after quoted duplicate ({quote})", reg.read_text(encoding="utf-8") == before)
    reg = d / "nokey.yaml"
    reg.write_text("# only a comment\nother: []\n", encoding="utf-8")
    r = run([str(d / "nk"), "--id", "nk", "--co-author", "claude"], reg)
    check("registry without top-level projects: key refused", r.returncode != 0 and not (d / "nk").exists())
    check("registry without projects: key left unchanged", reg.read_text(encoding="utf-8") == "# only a comment\nother: []\n")
    reg = d / "indented.yaml"
    reg.write_text("x:\n  projects:\n    - id: a\n", encoding="utf-8")
    r = run([str(d / "ik"), "--id", "ik", "--co-author", "claude"], reg)
    check("indented (nested) projects: key does not count", r.returncode != 0)

# Every project gets a private companion <id>-internal next to it: private records (such as the owner's
# ownership answers) live there and never in the project repo, which may be public.
with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    reg = d / "projects.yaml"
    reg.write_text("projects:\n", encoding="utf-8")
    proj, comp = d / "shop-app", d / "shop-app-internal"
    r = run([str(proj), "--id", "shop-app", "--co-author", "none"], reg)
    check("companion <id>-internal made next to the project, with ownership/", (comp / "ownership" / ".gitkeep").is_file())
    text = reg.read_text(encoding="utf-8")
    check("companion has its own registry entry and path", "- id: shop-app-internal" in text and f"path: '{comp}'" in text)
    check("companion entry carries the same co_author", text.count("co_author: none") == 2)
    check("output names the companion", "shop-app-internal" in r.stdout)

    r = run([str(d / "lib-internal"), "--id", "lib-internal", "--co-author", "claude"], reg)
    check("a project that is itself a companion gets no companion",
          r.returncode == 0 and not (d / "lib-internal-internal").exists())

    taken = d / "taken.yaml"
    taken.write_text("projects:\n  - id: web-internal\n", encoding="utf-8")
    r = run([str(d / "web"), "--id", "web", "--co-author", "claude"], taken)
    check("companion id already registered: refused before anything is made",
          r.returncode != 0 and not (d / "web").exists() and not (d / "web-internal").exists())

    old = d / "old.yaml"
    old.write_text(f"projects:\n  - id: old-app\n    path: '{d / 'old-app'}'\n", encoding="utf-8")
    (d / "old-app").mkdir()
    r = run([str(d / "old-app"), "--id", "old-app", "--co-author", "claude", "--internal-only"], old)
    text = old.read_text(encoding="utf-8")
    check("--internal-only adds the companion to an existing project",
          r.returncode == 0 and (d / "old-app-internal" / "ownership" / ".gitkeep").is_file())
    check("--internal-only adds only the companion's registry entry",
          "- id: old-app-internal" in text and text.count("- id: old-app\n") == 1)
    check("--internal-only leaves the project folder alone", not (d / "old-app" / "docs").exists())
    r = run([str(d / "ghost"), "--id", "ghost", "--co-author", "claude", "--internal-only"], old)
    check("--internal-only refused for a project missing from the registry",
          r.returncode != 0 and not (d / "ghost-internal").exists())

    r = run([str(d / "solo"), "--id", "solo", "--co-author", "claude", "--no-registry"], None)
    check("--no-registry still makes the companion folder", (d / "solo-internal" / "ownership" / ".gitkeep").is_file())

print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
