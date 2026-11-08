"""Test of repo_state.py: a read-only report on a git repository, always in temp dirs.
Git config is isolated (no system or user config); the "remote" is a local bare repository.
Usage: python test_repo_state.py   (exit 0 = pass)
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SCRIPT = Path(__file__).with_name("repo_state.py")
KEYS = [
    "repo", "branch", "detached", "unborn", "head", "default_branch", "on_default_branch",
    "upstream", "upstream_gone", "ahead", "behind", "last_fetch", "operation", "conflicted",
    "staged", "unstaged", "untracked", "stash_count", "commits", "merged_branches",
    "gone_branches", "remotes", "warnings",
]
fails = 0


def check(name, cond):
    global fails
    print(("  PASS  " if cond else "  FAIL  ") + name)
    if not cond:
        fails += 1


def make_env(tmp):
    cfg = tmp / "gitconfig"
    cfg.write_text("[user]\n\tname = Test\n\temail = test@example.invalid\n"
                   "[init]\n\tdefaultBranch = main\n", encoding="utf-8")
    env = dict(os.environ)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = str(cfg)
    return env


def git(cwd, *args, check_ok=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", env=ENV)
    if check_ok and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {r.stderr}")
    return r.stdout.strip()


def commit_file(cwd, name, text, msg):
    (Path(cwd) / name).write_text(text, encoding="utf-8")
    git(cwd, "add", name)
    git(cwd, "commit", "-q", "-m", msg)


def short(cwd, rev="HEAD"):
    return git(cwd, "rev-parse", "--short", rev)


def run(repo, *args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), str(repo), *args], capture_output=True,
                          text=True, encoding="utf-8", env=ENV)


def report(repo, *args):
    r = run(repo, "--json", *args)
    if r.returncode != 0:
        raise RuntimeError(f"repo_state failed: {r.stderr}")
    return json.loads(r.stdout)


def fingerprint(repo):
    out = {}
    base = Path(repo) / ".git"
    for p in sorted(base.rglob("*")):
        if p.is_file():
            out[p.relative_to(base).as_posix()] = (p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
    return out


with tempfile.TemporaryDirectory() as d:
    d = Path(d)
    ENV = make_env(d)

    # 1. plain folder
    plain = d / "plain"
    plain.mkdir()
    r = run(plain)
    check("plain folder: exit code 2", r.returncode == 2)
    check("plain folder: message on stderr", bool(r.stderr.strip()))

    # 2. fresh git init
    fresh = d / "fresh"
    fresh.mkdir()
    git(fresh, "init", "-q")
    s = report(fresh)
    check("fresh: unborn true", s["unborn"] is True)
    check("fresh: head null", s["head"] is None)
    check("fresh: branch main", s["branch"] == "main")
    check("fresh: commits empty", s["commits"] == [])

    # 3. clone of the bare remote with one pushed commit
    bare = d / "remote.git"
    bare.mkdir()
    git(bare, "init", "-q", "--bare")
    a = d / "a"
    git(d, "clone", "-q", str(bare), "a")
    commit_file(a, "one.txt", "1\n", "first")
    git(a, "push", "-q", "-u", "origin", "main")
    s = report(a)
    check("clone: upstream origin/main", s["upstream"] == "origin/main")
    check("clone: ahead 0", s["ahead"] == 0)
    check("clone: behind 0", s["behind"] == 0)
    check("clone: commit pushed", s["commits"][0]["pushed"] is True)
    check("clone: remote_branches", s["commits"][0]["remote_branches"] == ["origin/main"])
    check("clone: default_branch main", s["default_branch"] == "main")
    check("clone: on default branch", s["on_default_branch"] is True)
    check("clone: hash is rev-parse --short", s["head"] == short(a))

    # 4. one local commit
    commit_file(a, "two.txt", "2\n", "second")
    s = report(a)
    check("local commit: ahead 1", s["ahead"] == 1)
    check("local commit: newest not pushed", s["commits"][0]["pushed"] is False
          and s["commits"][0]["remote_branches"] == [])
    check("local commit: older pushed", s["commits"][1]["pushed"] is True)
    check("local commit: subject", s["commits"][0]["subject"] == "second")
    check("--commits limits the list", len(report(a, "--commits", "1")["commits"]) == 1)
    git(a, "push", "-q")

    # 5. behind, with and without --fetch
    b = d / "b"
    git(d, "clone", "-q", str(bare), "b")
    commit_file(b, "three.txt", "3\n", "third")
    git(b, "push", "-q")
    check("behind: 0 without --fetch", report(a)["behind"] == 0)
    s = report(a, "--fetch")
    check("behind: 1 with --fetch", s["behind"] == 1)
    check("behind: warning 6", any(w.startswith("behind origin/main by 1 commit(s)") for w in s["warnings"]))
    check("behind: last_fetch set", s["last_fetch"] is not None and s["last_fetch"].endswith(("Z", "+00:00")))
    git(a, "pull", "-q")

    # 6. staged, unstaged, untracked
    (a / "staged.txt").write_text("s\n", encoding="utf-8")
    git(a, "add", "staged.txt")
    (a / "one.txt").write_text("changed\n", encoding="utf-8")
    (a / "new.txt").write_text("n\n", encoding="utf-8")
    s = report(a)
    check("staged list", s["staged"] == ["staged.txt"])
    check("unstaged list", s["unstaged"] == ["one.txt"])
    check("untracked list", s["untracked"] == ["new.txt"])
    check("no conflicts here", s["conflicted"] == [])

    # 11. uncommitted changes on main
    check("on main with changes: warning 4", any(w.startswith("on the default branch with uncommitted changes")
                                               for w in s["warnings"]))

    # 12. stash
    git(a, "stash", "-q", "--include-untracked")
    check("stash_count 1", report(a)["stash_count"] == 1)
    check("clean after stash: no warning 4", not any("uncommitted" in w for w in report(a)["warnings"]))

    # 7. merge conflict
    c = d / "c"
    git(d, "clone", "-q", str(bare), "c")
    commit_file(c, "f.txt", "base\n", "base f")
    git(c, "push", "-q")
    git(c, "switch", "-q", "-c", "side")
    commit_file(c, "f.txt", "side\n", "side f")
    git(c, "switch", "-q", "main")
    commit_file(c, "f.txt", "main\n", "main f")
    git(c, "merge", "side", check_ok=False)
    s = report(c)
    check("conflict: operation merge", s["operation"] == "merge")
    check("conflict: file listed", s["conflicted"] == ["f.txt"])
    check("conflict: warning 2", "merge in progress: finish it or abort it before anything else" in s["warnings"])
    check("conflict: warning 3", "1 conflicted file(s)" in s["warnings"])
    git(c, "merge", "--abort")
    check("after abort: operation null", report(c)["operation"] is None)

    # 8. detached HEAD
    git(c, "switch", "-q", "--detach", "HEAD~1")
    s = report(c)
    check("detached: flag true", s["detached"] is True)
    check("detached: branch null", s["branch"] is None)
    check("detached: warning 1", "detached HEAD: commits made here are easy to lose; "
                                 "create a branch first (git switch -c <name>)" in s["warnings"])
    git(c, "switch", "-q", "main")

    # 9. merged and gone branches
    git(c, "switch", "-q", "-c", "done")
    commit_file(c, "done.txt", "d\n", "done work")
    git(c, "switch", "-q", "main")
    git(c, "merge", "-q", "--no-ff", "-m", "merge done", "done")
    git(c, "switch", "-q", "-c", "topic")
    commit_file(c, "topic.txt", "t\n", "topic work")
    git(c, "push", "-q", "-u", "origin", "topic")
    git(c, "switch", "-q", "main")
    git(c, "push", "origin", "--delete", "topic", "-q")
    git(c, "fetch", "--prune", "-q")
    s = report(c)
    check("merged_branches has done", "done" in s["merged_branches"])
    check("merged_branches excludes main and current", "main" not in s["merged_branches"])
    check("gone_branches has topic", s["gone_branches"] == ["topic"])
    git(c, "switch", "-q", "topic")
    s = report(c)
    check("gone upstream: upstream_gone true", s["upstream_gone"] is True)
    check("gone upstream: ahead/behind null", s["ahead"] is None and s["behind"] is None)
    check("gone upstream: warning 5", "upstream origin/topic is gone" in s["warnings"])
    git(c, "switch", "-q", "main")

    # 10. credentials stripped from remote URLs
    e = d / "e"
    e.mkdir()
    git(e, "init", "-q")
    git(e, "remote", "add", "origin", "https://user:hunter2pass@example.invalid/x.git")  # secret-gate: allow
    git(e, "remote", "add", "other", "https://tok3nvalue@example.invalid/y.git")  # secret-gate: allow
    r_text = run(e)
    r_json = run(e, "--json")
    check("url: password absent (text)", "hunter2pass" not in r_text.stdout)
    check("url: password absent (json)", "hunter2pass" not in r_json.stdout)
    check("url: token absent", "tok3nvalue" not in r_json.stdout)
    check("url: cleaned url present", "https://example.invalid/x.git" in r_json.stdout)
    check("remotes sorted by name", [x["name"] for x in json.loads(r_json.stdout)["remotes"]] == ["origin", "other"])
    check("never fetched: warning 7", any("never fetched" in w for w in json.loads(r_json.stdout)["warnings"]))

    # 13. read-only gate
    ro = d / "ro"
    git(d, "clone", "-q", str(bare), "ro")
    (ro / "one.txt").write_text("edited\n", encoding="utf-8")
    before = fingerprint(ro)
    git(ro, "update-ref", "refs/heads/probe", "HEAD")
    check("gate can fail: fingerprint changes on a write", fingerprint(ro) != before)
    git(ro, "update-ref", "-d", "refs/heads/probe")
    before = fingerprint(ro)
    r1 = run(ro)
    r2 = run(ro, "--json")
    check("gate: script ran (text and json)", r1.returncode == 0 and r2.returncode == 0)
    check("gate: .git unchanged without --fetch", fingerprint(ro) == before)

    # 14. key order, text format
    s = json.loads(r2.stdout)
    check("json: exactly the table keys, in order", list(s.keys()) == KEYS)
    text_lines = r1.stdout.splitlines()
    check("text: one key: line per field (warnings use WARNING: lines)",
          all(any(x.startswith(f"{k}:") for x in text_lines) for k in KEYS if k != "warnings"))
    check("text: commit line format", f"  {short(ro)} pushed " in r1.stdout or f"{short(ro)} pushed " in r1.stdout)
    check("bad argument: exit 2", run(ro, "--nope").returncode == 2)

print("ALL PASS" if fails == 0 else f"{fails} FAILED")
sys.exit(1 if fails else 0)
