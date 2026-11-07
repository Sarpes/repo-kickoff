"""Create the project skeleton folders and append a registry entry.

Usage: python scaffold_project.py <project-dir> --id <kebab-id> --co-author claude|none
           [--description TEXT] [--no-registry]
       python scaffold_project.py --print-registry-path

The registry file is read from the environment variable CLAUDE_REGISTRY; if it is
unset the default below is used. The script never overwrites an existing file and
never edits an existing registry entry; it only appends one. Standard library only.
"""
import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_REGISTRY = r"C:\Projects\workbench\registry\projects.yaml"
DOC_FOLDERS = ("handovers", "architecture", "guides", "artifacts", "archive")
ROOT_FILES = ("CLAUDE.md", "README.md", "DECISIONS.md", "AI-Agents.md")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CO_AUTHORS = ("claude", "none")


def registry_path() -> Path:
    return Path(os.environ.get("CLAUDE_REGISTRY") or DEFAULT_REGISTRY)


def entry_text(pid: str, path: Path, co_author: str, description: str) -> str:
    desc = description.replace("\\", "\\\\").replace('"', '\\"')
    return (
        f"\n  - id: {pid}\n"
        f"    path: '{path}'\n"
        f"    remote: ''\n"
        f'    description: "{desc}"\n'
        f"    stack: []\n"
        f"    status: active\n"
        f"    co_author: {co_author}\n"
        f"    plugins: []\n"
        f"    rules: []\n"
        f"    ports: []\n"
        f"    endpoints_used: []\n"
        f"    ui: []\n"
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir", nargs="?")
    ap.add_argument("--id")
    ap.add_argument("--co-author", choices=CO_AUTHORS, help="required: ask the user, do not guess")
    ap.add_argument("--description", default="")
    ap.add_argument("--no-registry", action="store_true", help="make folders only")
    ap.add_argument("--print-registry-path", action="store_true")
    a = ap.parse_args(argv)

    if a.print_registry_path:
        print(registry_path())
        return 0
    if not (a.project_dir and a.id and a.co_author):
        ap.error("project_dir, --id and --co-author are required")
    if not KEBAB.match(a.id):
        print(f"refused: id {a.id!r} must be lowercase kebab-case ASCII", file=sys.stderr)
        return 2

    reg = registry_path()
    text = ""
    if not a.no_registry:
        if not reg.is_file():
            print(f"refused: registry file not found: {reg} (set CLAUDE_REGISTRY or use --no-registry)", file=sys.stderr)
            return 2
        text = reg.read_text(encoding="utf-8")
        if not re.search(r"^projects:\s*(#.*)?$", text, re.M):
            print(f"refused: {reg} has no top-level 'projects:' key", file=sys.stderr)
            return 2
        if re.search(rf"""^\s*-\s*id:\s*(["']?){re.escape(a.id)}\1\s*(#.*)?$""", text, re.M):
            print(f"refused: id {a.id!r} already in {reg}", file=sys.stderr)
            return 2

    root = Path(a.project_dir).resolve()
    for f in DOC_FOLDERS:
        d = root / "docs" / f
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists():
            keep.touch()
    print(f"skeleton folders ready under {root / 'docs'}")

    if not a.no_registry:
        with open(reg, "a", encoding="utf-8", newline="") as fh:
            fh.write(("" if text.endswith("\n") else "\n") + entry_text(a.id, root, a.co_author, a.description or a.id))
        print(f"registry entry added to {reg} (co_author: {a.co_author})")

    missing = [f for f in ROOT_FILES if not (root / f).exists() and not (root / ".claude" / f).exists()]
    if missing:
        print("still to write at the root: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
