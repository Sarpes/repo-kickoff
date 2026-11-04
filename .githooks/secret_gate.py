"""Pre-commit secret gate (installed by repo-kickoff). Scans staged content."""
import re, subprocess, sys
NAME = re.compile(r"(^|/)(\.env(\..+)?|.*secret.*|.*credential.*|.*\.pem|.*\.key|id_rsa.*)$", re.I)
SAFE_NAME = re.compile(r"\.example$|\.sample$|\.template$|secret_gate\.py$", re.I)
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
