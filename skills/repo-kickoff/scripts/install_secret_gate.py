"""Install a pre-commit secret gate into a git repo, after proving it works.

Usage: python install_secret_gate.py <repo>

1. Builds a throwaway repo, installs the gate there, and checks that a commit
   containing a fake token is REFUSED and a clean commit is ACCEPTED.
2. Only if both hold: writes <repo>/.githooks/{pre-commit,secret_gate.py} and
   sets `git config core.hooksPath .githooks`.
The hook picks a Python by asking it to print a marker (a Windows Store stub
can exit 0 without running anything) and refuses the commit if none works.
A line ending in `secret-gate: allow` is skipped (for documented false positives).
"""
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GATE = r'''"""Pre-commit secret gate (installed by repo-kickoff). Scans staged content."""
import re, subprocess, sys
NAME = re.compile(r"(^|/)(\.env(\..+)?|[^/]*secrets?(\.[^/]*)?\.(json|ya?ml|toml|ini|cfg|txt|env|bat|ps1|sh)"
                  r"|client_secret[^/]*\.json|\.?credentials?(\.[^/]*)?\.(json|ya?ml|toml|ini)|[^/]*\.(pem|key|p12|pfx)"
                  r"|id_rsa[^/]*|\.netrc|\.npmrc|\.pypirc)$", re.I)
SAFE_NAME = re.compile(r"\.example$|\.sample$|\.template$|(^|/)\.githooks/secret_gate\.py$", re.I)  # only the gate itself
TEXT = re.compile(
    r"(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|sk-(ant-)?[A-Za-z0-9_-]{24,}"
    r"|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|(password|passwd|pwd|token|api_key|apikey|secret)\s*[=:]\s*['\"](?![$%{<])[^'\"\s]{6,}['\"])", re.I)
git = lambda *a: subprocess.run(["git", *a], capture_output=True).stdout
hits = []
for path in git("diff", "--cached", "--name-only", "--diff-filter=ACM", "-z").decode().split("\0"):
    if not path or SAFE_NAME.search(path):
        continue
    if NAME.search(path):
        hits.append(f"{path}: file name looks like a secret")
        continue
    try:
        text = git("show", f":{path}").decode("utf-8")
    except UnicodeDecodeError:
        continue
    for i, line in enumerate(text.splitlines(), 1):
        if TEXT.search(line) and not line.rstrip().endswith("secret-gate: allow"):
            hits.append(f"{path}:{i}: looks like a secret (value not shown)")
if hits:
    print("secret gate: commit REFUSED", *hits, "Move the value to an ignored file or env var.", sep="\n  ", file=sys.stderr)
    sys.exit(1)
'''

HOOK = """#!/bin/sh
# Pre-commit hook installed by repo-kickoff: run the secret gate with a Python that really runs.
# Each candidate must print a marker; a Windows Store stub answers to the name without running.
# Candidates are named one by one so every command this hook can run is readable in this file.
gate="$(git rev-parse --show-toplevel)/.githooks/secret_gate.py"
if [ "$(python3 -c "print('gate-ok')" 2>/dev/null)" = "gate-ok" ]; then exec python3 "$gate"; fi
if [ "$(python -c "print('gate-ok')" 2>/dev/null)" = "gate-ok" ]; then exec python "$gate"; fi
if [ "$(py -c "print('gate-ok')" 2>/dev/null)" = "gate-ok" ]; then exec py "$gate"; fi
echo "secret gate: no working Python found - commit refused (fail-closed)" >&2
exit 1
"""


ATTR = ".githooks/* text eol=lf"  # a CRLF checkout on Windows breaks `#!/bin/sh` ("\r: command not found")


def install(repo: Path):
    hooks = repo / ".githooks"
    hooks.mkdir(exist_ok=True)
    (hooks / "secret_gate.py").write_text(GATE, encoding="utf-8", newline="\n")
    (hooks / "pre-commit").write_text(HOOK, encoding="utf-8", newline="\n")
    attrs = repo / ".gitattributes"
    existing = attrs.read_text(encoding="utf-8").splitlines() if attrs.exists() else []
    if ATTR not in existing:
        attrs.write_text("\n".join(existing + [ATTR]) + "\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath", ".githooks"], check=True)
    subprocess.run(["git", "-C", str(repo), "update-index", "--chmod=+x", ".githooks/pre-commit"], capture_output=True)


def commit(repo: Path, name: str, content: str) -> bool:
    (repo / name).write_text(content, encoding="utf-8")
    g = lambda *a: subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                                  capture_output=True, text=True)
    g("add", name)
    ok = g("commit", "-qm", f"add {name}").returncode == 0
    if not ok:
        g("reset", "-q", name)
    return ok


def self_test() -> bool:
    fake = "ghp_" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4J3i2"  # assembled at runtime, not a real token
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        subprocess.run(["git", "init", "-q", str(t)], check=True)
        install(t)
        refused = not commit(t, "config.py", f'TOKEN = "{fake}"\n')
        accepted = commit(t, "app.py", 'TOKEN = "$EXAMPLE_TOKEN"\nprint("ok")\n')
    print(f"self-test: fake token refused={refused}, clean file accepted={accepted}")
    return refused and accepted


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    repo = Path(sys.argv[1]).resolve()
    if not (repo / ".git").exists():
        sys.exit(f"{repo} is not a git repo")
    if not self_test():
        sys.exit("self-test FAILED - gate not installed")
    install(repo)
    print(f"installed: {repo / '.githooks'} (core.hooksPath=.githooks) and `{ATTR}` in .gitattributes."
          " Commit .githooks/ and .gitattributes so clones get it; after a clone run: git config core.hooksPath .githooks")


if __name__ == "__main__":
    main()
