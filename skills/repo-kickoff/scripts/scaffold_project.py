"""Create the project skeleton folders, its private companion, and their registry entries.

Usage: python scaffold_project.py <project-dir> --id <kebab-id> --co-author claude|none
           [--description TEXT] [--no-registry] [--internal-only]
       python scaffold_project.py --print-registry-path

Every project gets a private companion folder <id>-internal next to it, with an ownership/ folder:
private records, such as the owner's own answers about how the project works, live there and never in
the project repo, which may be public. A project whose id already ends in -internal is itself a
companion and gets none. --internal-only adds just the companion (folder and registry entry) to a
project that is already registered.

The registry file is read from the environment variable CLAUDE_REGISTRY; if it is
unset the default below is used. The script never overwrites an existing file and
never edits an existing registry entry; it only appends. Every refusal happens before
anything is created. Standard library only.
"""
import argparse
import os
import re
import sys
from pathlib import Path

DEFAULT_REGISTRY = r"C:\Projects\workbench\registry\projects.yaml"
DOC_FOLDERS = ("handovers", "architecture", "guides", "artifacts", "archive")
ROOT_FILES = ("CLAUDE.md", "README.md", "DECISIONS.md", "AI-Agents.md")
COMPANION_SUFFIX = "-internal"
COMPANION_FOLDERS = ("ownership",)
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CO_AUTHORS = ("claude", "none")


def registry_path() -> Path:
    return Path(os.environ.get("CLAUDE_REGISTRY") or DEFAULT_REGISTRY)


def registered(text: str, pid: str) -> bool:
    return bool(re.search(rf"""^\s*-\s*id:\s*(["']?){re.escape(pid)}\1\s*(#.*)?$""", text, re.M))


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


def make_folders(base: Path, names) -> None:
    for name in names:
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        keep = d / ".gitkeep"
        if not keep.exists():
            keep.touch()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project_dir", nargs="?")
    ap.add_argument("--id")
    ap.add_argument("--co-author", choices=CO_AUTHORS, help="required: ask the user, do not guess")
    ap.add_argument("--description", default="")
    ap.add_argument("--no-registry", action="store_true", help="make folders only")
    ap.add_argument("--internal-only", action="store_true",
                    help="add only the private companion to a project that is already registered")
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
    is_companion = a.id.endswith(COMPANION_SUFFIX)
    if a.internal_only and is_companion:
        print(f"refused: {a.id!r} is itself a companion; --internal-only needs the project's own id", file=sys.stderr)
        return 2
    comp_id = None if is_companion else a.id + COMPANION_SUFFIX

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
        if a.internal_only and not registered(text, a.id):
            print(f"refused: --internal-only needs {a.id!r} in {reg}; scaffold the project first", file=sys.stderr)
            return 2
        if not a.internal_only and registered(text, a.id):
            print(f"refused: id {a.id!r} already in {reg}", file=sys.stderr)
            return 2
        if comp_id and registered(text, comp_id):
            print(f"refused: companion id {comp_id!r} already in {reg}", file=sys.stderr)
            return 2

    root = Path(a.project_dir).resolve()
    comp = root.parent / comp_id if comp_id else None
    entries = []
    if not a.internal_only:
        make_folders(root / "docs", DOC_FOLDERS)
        print(f"skeleton folders ready under {root / 'docs'}")
        entries.append(entry_text(a.id, root, a.co_author, a.description or a.id))
    if comp:
        make_folders(comp, COMPANION_FOLDERS)
        print(f"private companion {comp_id} ready at {comp} (ownership/); keep it a private repo, never linked "
              "from the project")
        entries.append(entry_text(comp_id, comp, a.co_author, f"Private companion of {a.id}"))

    if not a.no_registry:
        with open(reg, "a", encoding="utf-8", newline="") as fh:
            fh.write(("" if text.endswith("\n") else "\n") + "".join(entries))
        print(f"registry: {len(entries)} entr{'y' if len(entries) == 1 else 'ies'} added to {reg} "
              f"(co_author: {a.co_author})")

    if not a.internal_only:
        missing = [f for f in ROOT_FILES if not (root / f).exists() and not (root / ".claude" / f).exists()]
        if missing:
            print("still to write at the root: " + ", ".join(missing))
    if comp and not (comp / "README.md").exists():
        print(f"still to write in {comp_id}: README.md (what it holds, and that the project never links to it)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
