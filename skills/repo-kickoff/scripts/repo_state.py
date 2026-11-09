"""Report facts about a git repository without changing it.

Usage: python repo_state.py [REPO] [--json] [--fetch] [--commits N]

REPO defaults to the current folder; --commits defaults to 10. Exit code 2 when REPO is
not a git repository or an argument is bad, otherwise 0. The key fact per recent commit
is whether it is already pushed (contained in any remote-tracking branch). --fetch runs
`git fetch --all --prune --quiet` first and is the only option that contacts a remote or
changes anything (it updates remote-tracking refs). Every git call sets
GIT_OPTIONAL_LOCKS=0 so that `git status` does not rewrite the index. Standard library only.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CONFLICT_CODES = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}
URL_CREDENTIALS = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*://)[^/]*@")
STALE_AFTER_HOURS = 24
HOURS_UNTIL_DAYS = 48


def git(repo, *args):
    """Run git in repo; return stdout without its final newline, or None when git fails."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0")
    try:
        r = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
    except FileNotFoundError:
        print("error: the git executable was not found; install git and put it on PATH",
              file=sys.stderr)
        sys.exit(2)
    if r.returncode != 0:
        return None
    return r.stdout[:-1] if r.stdout.endswith("\n") else r.stdout


def lines(text):
    return [x for x in (text or "").split("\n") if x]


def ref_exists(repo, ref):
    return git(repo, "show-ref", "--verify", "--quiet", ref) is not None


def strip_credentials(url):
    return URL_CREDENTIALS.sub(r"\1", url)


def parse_status(raw):
    """Parse `git status --porcelain=v1 -z` into (conflicted, staged, unstaged, untracked)."""
    conflicted, staged, unstaged, untracked = [], [], [], []
    parts = raw.split("\0")
    i = 0
    while i < len(parts):
        entry = parts[i]
        i += 1
        if len(entry) < 4:
            continue
        xy, path = entry[:2], entry[3:]
        if "R" in xy or "C" in xy:
            i += 1  # a rename or copy is followed by its original path
        if xy == "??":
            untracked.append(path)
        elif xy in CONFLICT_CODES:
            conflicted.append(path)
        else:
            if xy[0] not in " ?!":
                staged.append(path)
            if xy[1] not in " ?!":
                unstaged.append(path)
    return sorted(conflicted), sorted(staged), sorted(unstaged), sorted(untracked)


def find_operation(git_dir):
    checks = (("MERGE_HEAD", "merge"), ("rebase-merge", "rebase"), ("rebase-apply", "rebase"),
              ("CHERRY_PICK_HEAD", "cherry-pick"), ("REVERT_HEAD", "revert"), ("BISECT_LOG", "bisect"))
    for name, op in checks:
        if (git_dir / name).exists():
            return op
    return None


def find_default_branch(repo):
    head = git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if head and head.startswith("origin/"):
        return head[len("origin/"):]
    for name in ("main", "master"):
        if ref_exists(repo, f"refs/heads/{name}"):
            return name
    return None


def local_branches(repo):
    """Return {name: (full upstream ref or '', gone)} for every local branch."""
    out = git(repo, "for-each-ref", "--format=%(refname:short)\t%(upstream)\t%(upstream:track)",
              "refs/heads") or ""
    result = {}
    for line in lines(out):
        name, upstream, track = (line.split("\t") + ["", ""])[:3]
        result[name] = (upstream, track == "[gone]")
    return result


def recent_commits(repo, count):
    out = git(repo, "log", f"-n{count}", "--format=%H\t%h\t%s") or ""
    commits = []
    for line in lines(out):
        full, short_hash, subject = line.split("\t", 2)
        refs = git(repo, "for-each-ref", "--contains", full, "--format=%(refname)\t%(symref)",
                   "refs/remotes") or ""
        names = []
        for ref_line in lines(refs):
            refname, symref = (ref_line.split("\t") + [""])[:2]
            if not symref:
                names.append(refname[len("refs/remotes/"):])
        commits.append({"hash": short_hash, "subject": subject, "pushed": bool(names),
                        "remote_branches": sorted(names)})
    return commits


def last_fetch_time(*git_dirs):
    """Newest FETCH_HEAD among the given dirs. A linked worktree keeps its own FETCH_HEAD in its
    git dir while the remote-tracking refs it updates are shared, so either file is evidence."""
    times = [d / "FETCH_HEAD" for d in git_dirs if (d / "FETCH_HEAD").is_file()]
    if not times:
        return None
    return datetime.fromtimestamp(max(f.stat().st_mtime for f in times), tz=timezone.utc)


def age_text(delta):
    hours = int(delta.total_seconds() // 3600)
    if hours < HOURS_UNTIL_DAYS:
        return f"{hours} hours"
    return f"{hours // 24} days"


def build_warnings(s, fetched_at, now):
    w = []
    if s["detached"]:
        w.append("detached HEAD: commits made here are easy to lose; create a branch first "
                 "(git switch -c <name>)")
    if s["operation"]:
        w.append(f"{s['operation']} in progress: finish it or abort it before anything else")
    if s["conflicted"]:
        w.append(f"{len(s['conflicted'])} conflicted file(s)")
    if s["on_default_branch"] and (s["conflicted"] or s["staged"] or s["unstaged"] or s["untracked"]):
        w.append("on the default branch with uncommitted changes: move them to a new branch "
                 "before committing")
    if s["upstream_gone"]:
        w.append(f"upstream {s['upstream']} is gone")
    if s["behind"]:
        w.append(f"behind {s['upstream']} by {s['behind']} commit(s): pull before starting new work")
    if fetched_at is not None:
        delta = now - fetched_at
        if delta.total_seconds() > STALE_AFTER_HOURS * 3600:
            w.append(f"remote information is from {age_text(delta)} ago; run with --fetch for "
                     "current ahead/behind and pushed status")
    elif s["remotes"]:
        w.append("remote information was never fetched; run with --fetch")
    return w


def collect(repo, count):
    top = git(repo, "rev-parse", "--show-toplevel")
    git_dir = Path(git(repo, "rev-parse", "--absolute-git-dir"))
    common = git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir")
    common_dir = Path(common) if common else git_dir

    unborn = git(repo, "rev-parse", "--verify", "--quiet", "HEAD") is None
    branch = git(repo, "symbolic-ref", "-q", "--short", "HEAD")
    default = find_default_branch(repo)
    branches = local_branches(repo)

    upstream_ref, gone = branches.get(branch, ("", False)) if branch else ("", False)
    upstream = upstream_ref.replace("refs/remotes/", "", 1).replace("refs/heads/", "", 1) or None
    ahead = behind = None
    if upstream_ref and not gone and not unborn:
        counts = git(repo, "rev-list", "--left-right", "--count", f"HEAD...{upstream_ref}")
        if counts:
            ahead, behind = (int(n) for n in counts.split())

    conflicted, staged, unstaged, untracked = parse_status(
        git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=normal") or "")

    merged = []
    if default:
        base = default if ref_exists(repo, f"refs/heads/{default}") else f"origin/{default}"
        out = git(repo, "for-each-ref", "--merged", base, "--format=%(refname:lstrip=2)", "refs/heads")
        merged = sorted(b for b in lines(out) if b not in (branch, default))

    remotes = []
    for name in sorted(lines(git(repo, "remote"))):
        url = git(repo, "remote", "get-url", name) or ""
        remotes.append({"name": name, "url": strip_credentials(url)})

    fetched_at = last_fetch_time(git_dir, common_dir)
    state = {
        "repo": str(Path(top)),
        "branch": branch,
        "detached": branch is None and not unborn,
        "unborn": unborn,
        "head": None if unborn else git(repo, "rev-parse", "--short", "HEAD"),
        "default_branch": default,
        "on_default_branch": branch is not None and branch == default,
        "upstream": upstream,
        "upstream_gone": bool(upstream_ref) and gone,
        "ahead": ahead,
        "behind": behind,
        "last_fetch": fetched_at.isoformat(timespec="seconds") if fetched_at else None,
        "operation": find_operation(git_dir),
        "conflicted": conflicted,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "stash_count": len(lines(git(repo, "stash", "list"))),
        "commits": [] if unborn else recent_commits(repo, count),
        "merged_branches": merged,
        "gone_branches": sorted(b for b, (up, g) in branches.items() if up and g),
        "remotes": remotes,
    }
    state["warnings"] = build_warnings(state, fetched_at, datetime.now(timezone.utc))
    return state


CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
NAMED_ESCAPES = {"\n": "\\n", "\r": "\\r", "\t": "\\t"}


def esc(s):
    """Make a repository-supplied string safe for a terminal or a line-oriented reader:
    control characters (newline, ESC, ...) become visible \\n, \\r, \\t or \\xNN."""
    return CONTROL_CHARS.sub(lambda m: NAMED_ESCAPES.get(m.group(), f"\\x{ord(m.group()):02x}"), str(s))


def text_value(value):
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(esc(v) for v in value) if value else "-"
    return esc(value)


def render_text(state):
    out = []
    for key, value in state.items():
        if key == "commits":
            out.append("commits:" + ("" if value else " -"))
            for c in value:
                flag = "pushed" if c["pushed"] else "NOT pushed"
                out.append(f"  {esc(c['hash'])} {flag} {esc(c['subject'])}")
        elif key == "remotes":
            out.append("remotes: " + (", ".join(f"{esc(r['name'])}={esc(r['url'])}" for r in value) or "-"))
        elif key == "warnings":
            out.extend(f"WARNING: {esc(w)}" for w in value)
        else:
            out.append(f"{key}: {text_value(value)}")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(description="Read-only report on a git repository.")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    p.add_argument("--fetch", action="store_true", help="run git fetch --all --prune --quiet first")
    p.add_argument("--commits", type=int, default=10, help="how many recent commits to list")
    args = p.parse_args()
    if args.commits < 0:
        p.error("--commits must not be negative")

    repo = Path(args.repo)
    if not repo.is_dir() or git(repo, "rev-parse", "--show-toplevel") is None:
        print(f"error: not a git repository: {args.repo}", file=sys.stderr)
        return 2

    if args.fetch and git(repo, "fetch", "--all", "--prune", "--quiet") is None:
        print("note: git fetch failed; remote information may be out of date", file=sys.stderr)

    state = collect(repo, args.commits)
    print(json.dumps(state, indent=2, ensure_ascii=False) if args.json else render_text(state))
    return 0


if __name__ == "__main__":
    sys.exit(main())
